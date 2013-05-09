# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Class to control the Belkin router."""

import logging
import os
import time
import urlparse

import ap_configurator
from selenium.common.exceptions import NoSuchElementException as \
    SeleniumNoSuchElementException


class BelkinAPConfigurator(ap_configurator.APConfigurator):
    """Base class for Belkin F5D8235-4 V2 router."""


    def _security_alert(self, alert):
        text = alert.text
        if "Invalid character" in text:
            alert.accept()
        else:
            raise RuntimeError('Invalid handler')


    def _open_landing_page(self):
        page_url = urlparse.urljoin(self.admin_interface_url,'home.htm')
        self.get_url(page_url, page_title='Setup Home')
        # Do we need to login?
        try:
            self.driver.find_element_by_link_text('Login')
        except SeleniumNoSuchElementException:
            # already logged in, return
            return
        login_element = self.driver.find_element_by_link_text('Login')
        login_element.click()
        xpath = '//input[@name="www_password"]'
        self.set_content_of_text_field_by_xpath('password', xpath,
                                                abort_check=True)
        self.click_button_by_id('submitBtn_submit')


    def get_supported_bands(self):
        return [{'band': self.band_2ghz,
                 'channels': ['Auto', 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}]


    def get_supported_modes(self):
        return [{'band': self.band_2ghz,
                 'modes': [self.mode_g | self.mode_b, self.mode_n,
                           self.mode_b | self.mode_g | self.mode_n]}]


    def get_number_of_pages(self):
        return 2


    def is_security_mode_supported(self, security_mode):
        return security_mode in (self.security_type_disabled,
                                 self.security_type_wpapsk,
                                 self.security_type_wep)


    def navigate_to_page(self, page_number):
        self._open_landing_page()
        if page_number == 1:
            page_url = urlparse.urljoin(self.admin_interface_url,
                                        'wireless_chan.htm')
            self.get_url(page_url, page_title='SSID')
        elif page_number == 2:
            page_url = urlparse.urljoin(self.admin_interface_url,
                                        'wireless_encrypt_64.htm')
            self.get_url(page_url, page_title='Security')
        else:
            raise RuntimeError('Invalid page number passed. Number of pages '
                               '%d, page value sent was %d' %
                               (self.get_number_of_pages(), page_number))


    def save_page(self, page_number):
        self.click_button_by_id('submitBtn_apply',
                                alert_handler=self._security_alert)
        if os.path.basename(self.driver.current_url) == 'post.cgi':
            # Give belkin some time to save settings.
            time.sleep(5)
        else:
            raise RuntimeError('Settings not applied. Invalid page %s' %
                               os.path.basename(self.driver.current_url))
        if (os.path.basename(self.driver.current_url) == 'wireless_chan.htm' or
        'wireless_encrypt_64.htm' or 'wireless_wpa_psk_wpa2_psk.htm'
        or 'wireless_encrypt_no.htm'):
            self.driver.find_element_by_xpath('//a[text()="Logout"]')
            self.click_button_by_xpath('//a[text()="Logout"]')


    def set_ssid(self, ssid):
        self.add_item_to_command_list(self._set_ssid, (ssid,), 1, 900)


    def _set_ssid(self, ssid):
        # Belkin does not accept special characters for SSID.
        # Invalid character: ~!@#$%^&*()={}[]|'\":;?/.,<>-
        xpath = '//input[@name="wl_ssid"]'
        self.set_content_of_text_field_by_xpath(ssid, xpath, abort_check=False)


    def set_channel(self, channel):
        self.add_item_to_command_list(self._set_channel, (channel,), 1, 900)


    def _set_channel(self, channel):
        position = self._get_channel_popup_position(channel)
        channel_choices = ['Auto', '1', '2', '3', '4', '5', '6', '7', '8',
                           '9', '10', '11']
        xpath = '//select[@name="wl_channel"]'
        self.select_item_from_popup_by_xpath(channel_choices[position], xpath)


    def set_mode(self, mode):
        self.add_item_to_command_list(self._set_mode, (mode,), 1, 900)


    def _set_mode(self, mode):
        mode_mapping = {self.mode_g | self.mode_b: '802.11g&802.11b',
                        self.mode_n: '802.11n only',
                        self.mode_b | self.mode_g | self.mode_n:
                        '802.11b&802.11g&802.11n'}
        mode_name = mode_mapping.get(mode)
        if not mode_name:
            raise RuntimeError('The mode %d not supported by router %s. ',
                               hex(mode), self.get_router_name())
        xpath = '//select[@name="wl_gmode"]'
        self.select_item_from_popup_by_xpath(mode_name, xpath)


    def set_ch_width(self, channel_width):
        """
        Adjusts the channel width.

        @param channel_width: the channel width
        """
        self.add_item_to_command_list(self._set_ch_width,(channel_width,),
                                      1, 900)


    def _set_ch_width(self, channel_width):
        channel_choice = ['20MHz', '20/40MHz']
        xpath = '//select[@name="wl_cwmmode"]'
        self.select_item_from_popup_by_xpath(channel_choice[channel_width],
                                             xpath)


    def set_radio(self, enabled=True):
        logging.debug('This router (%s) does not support radio',
                      self.get_router_name())
        return None


    def set_band(self, band):
        logging.debug('This router (%s) does not support multiple bands.',
                      self.get_router_name())
        return None


    def set_security_disabled(self):
        self.add_item_to_command_list(self._set_security_disabled, (), 2, 1000)


    def _set_security_disabled(self):
        xpath = '//select[@name="wl_sec_mode"]'
        self.select_item_from_popup_by_xpath('Disabled', xpath)


    def set_security_wep(self, key_value, authentication):
        self.add_item_to_command_list(self._set_security_wep,
                                      (key_value, authentication), 2, 1000)


    def _set_security_wep(self, key_value, authentication):
        popup = '//select[@name="wl_sec_mode"]'
        self.wait_for_object_by_xpath(popup)
        text_field = '//input[@name="wep64pp"]'
        self.select_item_from_popup_by_xpath('64bit WEP', popup,
                                             wait_for_xpath=text_field)
        self.set_content_of_text_field_by_xpath(key_value, text_field,
                                                abort_check=True)
        self.click_button_by_id('submitBtn_generate')


    def set_security_wpapsk(self, shared_key, update_interval=None):
        self.add_item_to_command_list(self._set_security_wpapsk,
                                      (shared_key, update_interval), 2, 900)


    def _set_security_wpapsk(self, shared_key, update_interval=None):
        popup = '//select[@name="wl_sec_mode"]'
        self.wait_for_object_by_xpath(popup)
        key_field = '//input[@name="wl_wpa_psk1"]'
        psk = '//select[@name="wl_auth"]'
        self.select_item_from_popup_by_xpath('WPA-PSK(no server)', popup,
                                             wait_for_xpath=key_field)
        self.select_item_from_popup_by_xpath('psk', psk)
        self.set_content_of_text_field_by_xpath(shared_key, key_field,
                                                abort_check=False)


    def is_visibility_supported(self):
        """
        Returns if AP supports setting the visibility (SSID broadcast).

        @return True if supported; False otherwise.
        """
        return False


    def is_update_interval_supported(self):
        """
        Returns True if setting the PSK refresh interval is supported.

        @return True is supported; False otherwise
        """
        return False
