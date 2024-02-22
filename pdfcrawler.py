import ttkbootstrap as ttk
from ttkbootstrap.constants import *

root = ttk.Window("system")

labelHello = ttk.Label(root, text="Hello, World!")
labelHello.pack()

root.mainloop()
