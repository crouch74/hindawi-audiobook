import os
import subprocess
import json
import math

class AudiobookBuilder:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def _get_duration_ms(self, filepath):
        """Returns duration in milliseconds."""
        cmd = [
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            filepath
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            duration_sec = float(result.stdout.strip())
            return int(duration_sec * 1000)
        except ValueError:
            print(f"Error reading duration for {filepath}")
            return 0

    def create_silence(self, duration_sec=1.0, output_path="silence.wav"):
        """Creates a silence wav file matching the format if needed, 
           but for ffmpeg concat, generating a null src is cleaner or just a silent file."""
        # Check if exists
        if os.path.exists(output_path):
            return output_path
            
        # Generate silence using ffmpeg lavfi
        # 16khz/mono to match MMS output usually, but safer to let ffmpeg handle conversion during concat
        # We'll make a standard 22050Hz mono silence
        cmd = [
            'ffmpeg', '-y', 
            '-f', 'lavfi', '-i', f'anullsrc=r=16000:cl=mono', 
            '-t', str(duration_sec), 
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path

    def build_m4b(self, chapters, metadata, cover_path, output_filename):
        """
        chapters: list of dict {'title': ..., 'file': 'path/to/wav'}
        metadata: dict {'title', 'author'}
        """
        print("Building M4B...")
        
        # 1. Generate Silence File
        silence_path = os.path.join(self.output_dir, "silence.wav")
        self.create_silence(1.0, silence_path)
        silence_duration = self._get_duration_ms(silence_path)

        # 2. Prepare Concat List and Metadata
        concat_list_path = os.path.join(self.output_dir, "files.txt")
        ffmetadata_path = os.path.join(self.output_dir, "metadata.txt")
        
        current_start = 0
        
        ffmetadata_content = [
            ";FFMETADATA1",
            f"title={metadata.get('title', 'Unknown')}",
            f"artist={metadata.get('author', 'Unknown')}",
            "genre=Audiobook",
            ""
        ]

        with open(concat_list_path, 'w') as f_concat:
            for idx, chapter in enumerate(chapters):
                file_path = chapter['file']
                # Convert to absolute path to avoid any path resolution issues
                abs_file_path = os.path.abspath(file_path)
                duration = self._get_duration_ms(abs_file_path)
                
                # Write to concat list with absolute path
                # escape filename
                safe_path = abs_file_path.replace("'", "'\\\\''")
                f_concat.write(f"file '{safe_path}'\n")
                
                # Update Metadata
                # Chapter entry
                # End is start + duration
                
                chapter_end = current_start + duration
                
                ffmetadata_content.extend([
                    "[CHAPTER]",
                    "TIMEBASE=1/1000",
                    f"START={current_start}",
                    f"END={chapter_end}",
                    f"title={chapter['title']}",
                    ""
                ])
                
                current_start = chapter_end
                
                # Add silence between chapters (except last)
                if idx < len(chapters) - 1:
                    abs_silence_path = os.path.abspath(silence_path)
                    f_concat.write(f"file '{abs_silence_path}'\n")
                    current_start += silence_duration

        with open(ffmetadata_path, 'w', encoding='utf-8') as f_meta:
            f_meta.write("\n".join(ffmetadata_content))

        # 3. Run FFmpeg
        # Inputs:
        # -f concat files.txt (audio)
        # cover (image)
        # metadata.txt
        
        # We need to re-encode to AAC (aac_he or aac)
        # -c:a aac -b:a 64k
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0', '-i', concat_list_path,
        ]
        
        if cover_path and os.path.exists(cover_path):
            cmd.extend(['-i', cover_path])
            # map audio from 0, video (cover) from 1
            map_args = ['-map', '0:a', '-map', '1:v']
            disposition = ['-disposition:v', 'attached_pic']
        else:
            map_args = ['-map', '0:a']
            disposition = []

        cmd.extend([
            '-i', ffmetadata_path,
            '-map_metadata', '1' if (cover_path and os.path.exists(cover_path)) else '1', 
             # wait, if cover is input 1, metadata is input 2
        ])
        
        # Correct index for metadata
        # 0: concat
        # 1: cover (optional)
        # 2: metadata (if cover) OR 1: metadata (if no cover)
        
        metadata_index = 2 if (cover_path and os.path.exists(cover_path)) else 1
        
        # fix cmd building
        cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list_path]
        if cover_path and os.path.exists(cover_path):
             cmd.extend(['-i', cover_path])
        cmd.extend(['-i', ffmetadata_path])
        
        cmd.extend(['-map_metadata', str(metadata_index)])
        cmd.extend(['-map', '0:a'])
        if cover_path and os.path.exists(cover_path):
            cmd.extend(['-map', '1:v', '-disposition:v', 'attached_pic'])
            
        cmd.extend(['-c:a', 'aac', '-b:a', '64k']) # Encode audio
        cmd.extend(['-c:v', 'copy']) # Copy image if present (jpg/png)
        
        cmd.append(output_filename)
        
        print(f"Running ffmpeg to create {output_filename}...")
        # print(" ".join(cmd))
        subprocess.run(cmd, check=True)
        print("Done.")
