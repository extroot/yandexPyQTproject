import os
import sys
import json
import logging
import sqlite3

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication

from menu import PrimaryDrawerItem
from menu import ExpandableDrawerItem

# Getting variables from the environment
log_level = os.environ.get('BLL_LOGLEVEL', 'DEBUG')
log_file = os.environ.get('BLL_LOGFILE', '')
file_mode = os.environ.get('BLL_LOGFILE_MODE', 'a')
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Logger creation
logging.basicConfig(filename=log_file,
                    filemode=file_mode,
                    format=log_format,
                    level=log_level)
logger = logging.getLogger(__name__)

# Project files and relative image folder path
files = {
    'menu_file': 'menu.json',
    'uic_file': 'design.ui',
    'database_file': 'database.db',
    'logo_file': 'images/logo.png'
}
images_folder = 'images/'


class MainActivity(QMainWindow):
    def __init__(self):
        super().__init__()

        # Checking for Project Files
        file_error = False
        for name, filename in files.items():
            if not os.path.isfile(filename):
                logger.error(f'Не найден {name} {filename}')
                file_error = True
        if file_error:
            logger.fatal('Обнаружено отсутствие необходимых файлов')
            exit(-1)
        logger.info('Проверка наличия необходимых файлов выполнена')

        # uic file connection
        try:
            uic.loadUi(files['uic_file'], self)
        except Exception as e:
            logger.fatal(f'Произошла ошибка во время чтения uic файла {files["uic_file"]}')
            logger.debug(e)
            exit(-1)

        # Retrieving Menu Data from menu json file
        try:
            with open(files['menu_file'], 'r', encoding='utf-8') as menu_file:
                menu_json = json.load(menu_file)
        except Exception as e:
            logger.fatal(f'Произошла ошибка во время чтения файла меню {files["menu_file"]}')
            logger.debug(e)
            exit(-1)
        logger.info('Загрузка файла меню выполнена')

        # Connecting to the database and getting the cursor
        try:
            self.con = sqlite3.connect(files['database_file'])
            self.cur = self.con.cursor()
        except Exception as e:
            logger.error(f'Произошла ошибка при подключении базы данных {files["database_file"]}')
            logger.debug(e)
            exit(-1)
        logger.info('Подключение базы данных выполнено')

        # Setting the application icon and title
        self.setWindowIcon(QIcon(files['logo_file']))
        self.setWindowTitle('Cube Guide')

        # Creation of the necessary layouts
        self.formLayout = QFormLayout()
        self.last = None

        self.groupBox = QGroupBox("")

        self.widget = QWidget()
        self.vbox = QVBoxLayout()

        self.vbox.setAlignment(Qt.AlignTop)

        self.scrollArea.setWidget(self.groupBox)
        self.scrollArea.setWidgetResizable(True)

        self.scrollArea_2.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea_2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_2.setWidgetResizable(True)

        self.scrollArea_2.setWidget(self.widget)
        self.widget.setLayout(self.vbox)

        def process_menu_item(item):
            """
            Creates menu buttons by json description and adds it to QVBoxLayout

            Item example:
            {
              "text": "Text",
              "level": 1,
              "expandable": false,
              "mode": "mode"
            }

            Standard units:
             text - button text,
             level - number of left indents
             expandable - ExpandableDrawerItem if True else PrimaryDrawerItem
             mode - PrimaryDrawerItem's callback data

            Addiction units:
             expanded - if True automatically opens ExpandableDrawerItem on create
             selected - if True automatically selects PrimaryDrawerItem on create

            If the item is expandable, it is recursively processed sub items

            :param item: json description

            :return: ExpandableDrawerItem or PrimaryDrawerItem
            """

            if item['expandable']:
                out = ExpandableDrawerItem(text=item['text'], level=item['level'])
                
                if 'expanded' in item and item['expanded']:
                    out.expand()

                self.vbox.addWidget(out.btn)
                out.add_sub_items([process_menu_item(x) for x in item['sub_items']])
            else:
                out = PrimaryDrawerItem(text=item['text'], level=item['level'], mode=item['mode'])

                out.connect(self.action)
                self.vbox.addWidget(out.btn)

                if 'selected' in item and item['selected']:
                    out.action()
            return out

        # Creating a menu using a recursive function process_menu_item
        self.menu = []
        for element in menu_json['items']:
            self.menu.append(process_menu_item(element))
        logger.info('Обработка меню выполнена')

    def action(self, button):
        """
        Handles a menu button press and get and receives data from the database for rendering

        :param button: ExpandableDrawerItem or PrimaryDrawerItem
        """

        # Removing highlight from the last button
        if self.last is not None:
            self.last.set_selection(False)
        self.last = button

        # Setting the highlight of the current button
        button.set_selection(True)

        mode = button.mode
        pic_name = None
        title_mode = None

        try:
            # Receiving image filename template and title mode
            sql = """SELECT pic_name, title_mode FROM modes WHERE name = ?"""
            result = self.cur.execute(sql, (mode, )).fetchone()
            if result:
                pic_name, title_mode = result

            # Receiving list of titles
            sql = """SELECT title FROM formulas WHERE mode = ?"""
            result = self.cur.execute(sql, (title_mode, )).fetchall()
            titles = []
            for item in result:
                titles.append(item[0])

            # Receiving list of formulas
            sql = """SELECT text FROM formulas WHERE mode = ?"""
            result = self.cur.execute(sql, (mode, )).fetchall()
            formulas = []
            for item in result:
                formulas.append(item[0])

            if not formulas:
                logger.warning(f'Не найдены формулы для {mode}')
                return

            if not titles:
                logger.warning(f'Не найдены заголовки для {mode}')

        except Exception as e:
            logger.error('Произошла ошибка при получении данных из базы данных.')
            logger.debug(e)
            return

        # Start rendering
        self.draw(pic_name, formulas, titles)

    def draw(self, pic_name, formulas, titles):
        """
        Renders pictures, formulas and titles

        :param pic_name: image filename template
        :param formulas: list of strings formulas
        :param titles: list of strings titles
        :return:
        """

        # Remove all rows from formLayout
        for _ in range(self.formLayout.rowCount()):
            self.formLayout.removeRow(0)

        for i, text in enumerate(formulas):
            image_filename = images_folder + pic_name.format(i)
            text = text

            if not text:
                continue

            # Check for image existence
            if not os.path.isfile(image_filename):
                logger.warning(f'Не найдено изображения для {pic_name.format(i)}')

            # Create title
            if titles and titles[i]:
                title_label = QLabel(titles[i], self)
                title_label.setAlignment(Qt.AlignHCenter)
                title_label.setStyleSheet("text-align: center; padding: 3px;"
                                          " font: roboto; font-size: 19px; color: black;")

                self.formLayout.addRow(title_label)

            # pixmap = QPixmap(image_filename).scaled(100, 100)
            pixmap = QPixmap(image_filename).scaledToWidth(100)
            image = QLabel(self)
            image.setPixmap(pixmap)

            label = QLabel(text, self)
            label.setStyleSheet("text-align: left; padding: 3px;"
                                " font: roboto; font-size: 15px; color: black;")

            self.formLayout.addRow(image, label)
        self.groupBox.setLayout(self.formLayout)


if __name__ == '__main__':
    sys_argv = sys.argv

    app = QApplication(sys.argv)
    ex = MainActivity()
    ex.show()

    sys.exit(app.exec_())
