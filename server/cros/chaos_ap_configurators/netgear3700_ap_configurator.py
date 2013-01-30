# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import netgear_WNDR_dual_band_configurator
from netgear_WNDR_dual_band_configurator import *


class Netgear3700APConfigurator(netgear_WNDR_dual_band_configurator.
                                NetgearDualBandAPConfigurator):
    """Derived class to control Netgear 3700 router."""


    def _alert_handler(self, alert):
        """Checks for any modal dialogs which popup to alert the user and
        either raises a RuntimeError or ignores the alert.

        Args:
          alert: The modal dialog's contents.
        """
        text = alert.text
        #  We ignore warnings that we get when we disable visibility or security
        #  changed to WEP, WPA Personal or WPA Enterprise.
        if 'The WEP security can only be supported on one SSID' in text:
            alert.accept()
        else:
            super(Netgear3700APConfigurator, self)._alert_handler(alert)


    def _get_settings_page(self):
        frame1 = self.driver.find_element_by_xpath('//frame[@name="contents"]')
        frame2 = self.driver.switch_to_frame(frame1)
        xpath = '//a[text()="Wireless Settings"]'
        self.click_button_by_xpath(xpath)
        default = self.driver.switch_to_default_content()
        setframe = self.driver.find_element_by_xpath(
                   '//frame[@name="formframe"]')
        settings = self.driver.switch_to_frame(setframe)


    def save_page(self, page_number):
        self.click_button_by_xpath('//input[@name="Apply"]',
                                   alert_handler=self._alert_handler)


    def get_supported_bands(self):
        return [{'band': self.band_2ghz,
                 'channels': ['Auto', 1, 2, 3, 4, 5, 6, 7, 8, 9 , 10, 11]},
                {'band': self.band_5ghz,
                 'channels': [36, 40, 44, 48, 149, 153, 157, 161]}]


    def get_supported_modes(self):
        return [{'band': self.band_5ghz,
                 'modes': [self.mode_130, self.mode_300, self.mode_54]},
                {'band': self.band_2ghz,
                 'modes': [self.mode_130, self.mode_300, self.mode_54]}]


    def navigate_to_page(self, page_number):
        self.driver.get(self.admin_interface_url)
        if self.driver.title.find('NETGEAR') != -1:
            self.wait_for_object_by_xpath('//frame[@name="topframe"]',
                                          wait_time=60)
        else:
            raise RuntimeError('Unable to open landing page.')
        self._get_settings_page()


    def _switch_to_default(self):
        self.driver.switch_to_default_content()
        self._get_settings_page()


    def _set_channel(self, channel):
        self._switch_to_default()
        position = self._get_channel_popup_position(channel)
        channel_choices = ['Auto', '01', '02', '03', '04', '05', '06', '07',
                           '08', '09', '10', '11']
        xpath = '//select[@name="w_channel"]'
        if self.current_band == self.band_5ghz:
            xpath = '//select[@name="w_channel_an"]'
            channel_choices = ['36', '40', '44', '48', '149', '153',
                               '157', '161']
        self.select_item_from_popup_by_xpath(channel_choices[position], xpath)


    def _set_security_wep(self, value, authentication):
        self._switch_to_default()
        xpath = ('//input[@name="security_type" and @value="WEP"]')
        text = '//input[@name="passphraseStr"]'
        button = '//input[@name="Generate"]'
        if self.current_band == self.band_5ghz:
            xpath = ('//input[@name="security_type_an" and @value="WEP"]')
            text = '//input[@name="passphraseStr_an"]'
            button = '//input[@name="Generate_an"]'
        try:
            self.click_button_by_xpath(xpath, alert_handler=self._alert_handler)
        except Exception, e:
            raise RuntimeError('For WEP the mode should be 54Mbps. %s' % e)
        self.set_content_of_text_field_by_xpath(value, text, abort_check=True)
        self.click_button_by_xpath(button, alert_handler=self._alert_handler)
