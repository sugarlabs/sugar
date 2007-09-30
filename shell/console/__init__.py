from console import Console

console = None

def show():
    global console
    if not console:
        console = Console()
    console.show()    

def hide():
    if console:
        console.hide() 

def toggle_visibility():
    if not console or not console.props.visible:
        show()
    else:
        hide()

