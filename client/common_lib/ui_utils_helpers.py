from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import ui_utils
from autotest_lib.client.cros.input_playback import keyboard


class UI_Helper_Handler(object):

    def __init__(self, ui_handler=None, chrome=None):
        """ui_handler or chrome must be provided. ui_handler is an already
        existing ui object."""
        if not self.ui_handler and chrome:
            self.ui = ui_utils.UI_Handler()
            self.ui.start_ui_root(chrome)
        elif not chrome and ui_handler:
            self.ui = ui_handler
        else:
            raise error.TestError(
                "Either the chrome object or ui_handler must be provided.")
        self._keyboard = None

    def print_to_custom_printer(self, printer_name, isPDF=False):
        """Open the printer menu, select the printer given and click print."""
        self.open_printer_menu()
        self.open_see_more_print_sub_menu()
        self.select_printer_from_see_more_menu(printer_name)
        self.wait_for_print_ready()
        self.click_print(isPDF)
        if self._keyboard:
            self._keyboard.close()

    def open_printer_menu(self):
        self.ui.doDefault_on_obj('Chrome')
        self.ui.wait_for_ui_obj('/Print/', role='menuItem', isRegex=True)
        self.ui.doDefault_on_obj('/Print/', isRegex=True)
        self.wait_for_print_ready()

    def wait_for_print_ready(self):
        self.ui.wait_for_ui_obj('Fit to width', role='button')
        self.ui.wait_for_ui_obj('Loading preview', remove=True)

    def open_see_more_print_sub_menu(self):
        """For now must pivot there with the KB."""
        if not self.is_print_menu_open():
            raise error.TestError(
                "Cannot open See more print menu when print screen not open")
        if not self._keyboard:
            self._keyboard = keyboard.Keyboard()
        for i in range(4):
            self._keyboard.press_key('tab')
        self._keyboard.press_key('down')
        self._keyboard.press_key('enter')

    def select_printer_from_see_more_menu(self, printer_name):
        """Click a printer from the "see more" sub menu within print page."""
        if not self.is_see_more_menu_open():
            raise error.TestError(
                "Cannot select printer from sub menu as its not open.")
        self.ui.wait_for_ui_obj(printer_name, role='cell')
        self.ui.doDefault_on_obj(printer_name, role='cell')
        self.ui.wait_for_ui_obj(printer_name, role='cell', remove=True)
        # Wait for the "Setting up " loading icon to finish
        self.ui.wait_for_ui_obj('Setting up ', remove=True)

    def click_print(self, isPDF=False):
        """Click the print button. Click save if PDF."""
        if not self.is_print_menu_open():
            raise error.TestError(
                "Cannot open See more print menu when print screen not open")

        self.ui.doDefault_on_obj('Save' if isPDF else 'Print', role='button')
        if isPDF:
            pass  # TODO implement the save menu

    def is_see_more_menu_open(self):
        """Return True if the print menu is open."""
        try:
            self.ui.wait_for_ui_obj("Select a destination", role="dialog")
        except error.TestError:
            return False
        return True

    def is_print_menu_open(self):
        """Return True if the print menu is open."""
        return self.ui.item_present("Print", role="window")
