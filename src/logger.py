from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "error": "bold red",
    "success": "bold green",
})

console = Console(theme=custom_theme)

def log_info(message):
    console.print(message, style="info")

def log_success(message):
    console.print(message, style="success")

def log_error(message):
    console.print(message, style="error")

def log_warning(message):
    console.print(message, style="warning")
