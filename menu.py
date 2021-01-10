from PyQt5.QtWidgets import QPushButton


class PrimaryDrawerItem:
    def __init__(self, text='', level=1, mode='', selected=False):
        self.level = level
        self.mode = mode
        self.func = lambda *args: None

        self.btn = QPushButton()
        self.set_selection(selected)
        self.set_text(text)

        self.btn.clicked.connect(self.action)

        if selected:
            self.action()

    def set_text(self, text):
        self.btn.setText(' ' * 4 * (self.level - 1) + text)

    def set_visible(self, visible):
        self.btn.setVisible(visible)

    def action(self):
        """
        Calls the connected function when clicked
        """
        self.func(self)

    def set_selection(self, selected=False):
        if selected:
            self.btn.setStyleSheet("QPushButton { text-align: left; padding: 3px;"
                                   " background-color: #1F2196F3; border-style: None;"
                                   " color: #2196F3; font: roboto; font-size: 14px;}")
        else:
            self.btn.setStyleSheet("QPushButton {text-align: left; padding: 3px;"
                                   " background-color: white; border-style: None;"
                                   " color: black; font: roboto; font-size: 14px;}")

    def connect(self, func):
        self.func = func


class ExpandableDrawerItem(PrimaryDrawerItem):
    def __init__(self, text='', level=1, sub_items=None, expanded=False):
        self.text_close = text + ' 🡆'
        self.text_open = text + ' 🡇'
        self.opened = not expanded
        self.sub_items = sub_items

        super().__init__(text=self.text_close, level=level)
        self.connect(self.expand)
        self.expand()

    def expand(self, other=None):
        self.opened = not self.opened

        if self.opened:
            self.set_text(self.text_open)
        else:
            self.set_text(self.text_close)

        if not self.sub_items:
            return

        for item in self.sub_items:
            if isinstance(item, ExpandableDrawerItem):
                if item.opened:
                    item.expand()

            item.set_visible(self.opened)

    def add_sub_items(self, sub_items):
        """
        Sets sub items
        :param sub_items: List of DrawerItems (PrimaryDrawerItem or ExpandableDrawerItem)
        """

        self.sub_items = sub_items
        self.expand()
        self.expand()
