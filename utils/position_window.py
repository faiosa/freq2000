def position_window_at_centre(window, width, height):
    # Calculate the position to center the window on the screen
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    window_width = width
    window_height = height
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    return f"{window_width}x{window_height}+{x}+{y}"
