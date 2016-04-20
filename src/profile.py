from list_items import MessageItem, ContactItem, FileTransferItem
from PySide import QtCore, QtGui
from tox import Tox
import os
from messages import *
from settings import *
from toxcore_enums_and_consts import *
from ctypes import *
from util import curr_time, log, Singleton, curr_directory, convert_time
from tox_dns import tox_dns
from history import *
from file_transfers import *
import time
import calls
import avwidgets


class Contact(object):
    """
    Class encapsulating TOX contact
    Properties: name (alias of contact or name), status_message, status (connection status)
    widget - widget for update
    """

    def __init__(self, name, status_message, widget, tox_id):
        """
        :param name: name, example: 'Toxygen user'
        :param status_message: status message, example: 'Toxing on toxygen'
        :param widget: ContactItem instance
        :param tox_id: tox id of contact
        """
        self._name, self._status_message = name, status_message
        self._status, self._widget = None, widget
        self._widget.name.setText(name)
        self._widget.status_message.setText(status_message)
        self._tox_id = tox_id
        self.load_avatar()

    # -----------------------------------------------------------------------------------------------------------------
    # name - current name or alias of user
    # -----------------------------------------------------------------------------------------------------------------

    def get_name(self):
        return self._name

    def set_name(self, value):
        self._name = value.decode('utf-8')
        self._widget.name.setText(self._name)
        self._widget.name.repaint()

    name = property(get_name, set_name)

    # -----------------------------------------------------------------------------------------------------------------
    # Status message
    # -----------------------------------------------------------------------------------------------------------------

    def get_status_message(self):
        return self._status_message

    def set_status_message(self, value):
        self._status_message = value.decode('utf-8')
        self._widget.status_message.setText(self._status_message)
        self._widget.status_message.repaint()

    status_message = property(get_status_message, set_status_message)

    # -----------------------------------------------------------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------------------------------------------------------

    def get_status(self):
        return self._status

    def set_status(self, value):
        self._widget.connection_status.data = self._status = value
        self._widget.connection_status.repaint()

    status = property(get_status, set_status)

    # -----------------------------------------------------------------------------------------------------------------
    # TOX ID. WARNING: for friend it will return public key, for profile - full address
    # -----------------------------------------------------------------------------------------------------------------

    def get_tox_id(self):
        return self._tox_id

    tox_id = property(get_tox_id)

    # -----------------------------------------------------------------------------------------------------------------
    # Avatars
    # -----------------------------------------------------------------------------------------------------------------

    def load_avatar(self):
        """
        Tries to load avatar of contact or uses default avatar
        """
        avatar_path = '{}.png'.format(self._tox_id[:TOX_PUBLIC_KEY_SIZE * 2])
        os.chdir(ProfileHelper.get_path() + 'avatars/')
        if not os.path.isfile(avatar_path):  # load default image
            avatar_path = 'avatar.png'
            os.chdir(curr_directory() + '/images/')
        pixmap = QtGui.QPixmap(QtCore.QSize(64, 64))
        pixmap.load(avatar_path)
        self._widget.avatar_label.setScaledContents(False)
        self._widget.avatar_label.setPixmap(pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio))
        self._widget.avatar_label.repaint()

    def reset_avatar(self):
        avatar_path = (ProfileHelper.get_path() + 'avatars/{}.png').format(self._tox_id[:TOX_PUBLIC_KEY_SIZE * 2])
        if os.path.isfile(avatar_path):
            os.remove(avatar_path)
            self.load_avatar()

    def set_avatar(self, avatar):
        avatar_path = (ProfileHelper.get_path() + 'avatars/{}.png').format(self._tox_id[:TOX_PUBLIC_KEY_SIZE * 2])
        with open(avatar_path, 'wb') as f:
            f.write(avatar)
        self.load_avatar()


class Friend(Contact):
    """
    Friend in list of friends. Can be hidden, properties 'has unread messages' and 'has alias' added
    """

    def __init__(self, message_getter, number, *args):
        """
        :param message_getter: gets messages from db
        :param number: number of friend.
        """
        super(Friend, self).__init__(*args)
        self._number = number
        self._new_messages = False
        self._visible = True
        self._alias = False
        self._message_getter = message_getter
        self._corr = []
        self._unsaved_messages = 0
        self._history_loaded = False

    def __del__(self):
        self.set_visibility(False)
        del self._widget
        del self._message_getter

    # -----------------------------------------------------------------------------------------------------------------
    # History support
    # -----------------------------------------------------------------------------------------------------------------

    def load_corr(self, first_time=True):
        """
        :param first_time: friend became active, load first part of messages
        """
        if (first_time and self._history_loaded) or (not hasattr(self, '_message_getter')):
            return
        data = self._message_getter.get(PAGE_SIZE)
        if data is not None and len(data):
            data.reverse()
        else:
            return
        data = map(lambda tupl: TextMessage(*tupl), data)
        self._corr = data + self._corr
        self._history_loaded = True

    def get_corr_for_saving(self):
        """
        Get data to save in db
        :return: list of unsaved messages or []
        """
        if hasattr(self, '_message_getter'):
            del self._message_getter
        messages = filter(lambda x: x.get_type() <= 1, self._corr)
        return map(lambda x: x.get_data(), messages[-self._unsaved_messages:]) if self._unsaved_messages else []

    def get_corr(self):
        return self._corr[:]

    def append_message(self, message):
        """
        :param message: tuple (message, owner, unix_time, message_type)
        """
        self._corr.append(message)
        if message.get_type() <= 1:
            self._unsaved_messages += 1

    def get_last_message(self):
        messages = filter(lambda x: x.get_type() <= 1 and not x.get_owner(), self._corr)
        if messages:
            return messages[-1].get_data()[0]
        else:
            return ''

    def clear_corr(self):
        """
        Clear messages list
        """
        if hasattr(self, '_message_getter'):
            del self._message_getter
        self._corr = filter(lambda x: x.get_type() > 1, self._corr)
        self._unsaved_messages = 0

    def update_transfer_data(self, file_number, status):
        """
        Update status of active transfer
        """
        try:
            tr = filter(lambda x: x.get_type() == 2 and x.is_active(file_number), self._corr)[0]
            tr.set_status(status)
        except:
            pass

    # -----------------------------------------------------------------------------------------------------------------
    # Alias support
    # -----------------------------------------------------------------------------------------------------------------

    def set_name(self, value):
        """
        Set new name or ignore if alias exists
        :param value: new name
        """
        if not self._alias:
            super(self.__class__, self).set_name(value)

    def set_alias(self, alias):
        self._alias = bool(alias)

    # -----------------------------------------------------------------------------------------------------------------
    # Visibility in friends' list
    # -----------------------------------------------------------------------------------------------------------------

    def get_visibility(self):
        return self._visible

    def set_visibility(self, value):
        self._visible = value

    visibility = property(get_visibility, set_visibility)

    # -----------------------------------------------------------------------------------------------------------------
    # Unread messages from friend
    # -----------------------------------------------------------------------------------------------------------------

    def get_messages(self):
        return self._new_messages

    def set_messages(self, value):
        self._widget.connection_status.messages = self._new_messages = value
        self._widget.connection_status.repaint()

    messages = property(get_messages, set_messages)

    # -----------------------------------------------------------------------------------------------------------------
    # Friend's number (can be used in toxcore)
    # -----------------------------------------------------------------------------------------------------------------

    def get_number(self):
        return self._number

    def set_number(self, value):
        self._number = value

    number = property(get_number, set_number)


class Profile(Contact, Singleton):
    """
    Profile of current toxygen user. Contains friends list, tox instance
    """
    def __init__(self, tox, screen):
        """
        :param tox: tox instance
        :param screen: ref to main screen
        """
        super(Profile, self).__init__(tox.self_get_name(),
                                      tox.self_get_status_message(),
                                      screen.user_info,
                                      tox.self_get_address())
        self._screen = screen
        self._messages = screen.messages
        self._tox = tox
        self._file_transfers = {}  # dict of file transfers. key - tuple (friend_number, file_number)
        self._call = calls.AV(tox)  # data about calls
        settings = Settings.get_instance()
        self._show_online = settings['show_online_friends']
        screen.online_contacts.setChecked(self._show_online)
        aliases = settings['friends_aliases']
        data = tox.self_get_friend_list()
        self._history = History(tox.self_get_public_key())  # connection to db
        self._friends, self._active_friend = [], -1
        for i in data:  # creates list of friends
            tox_id = tox.friend_get_public_key(i)
            if not self._history.friend_exists_in_db(tox_id):
                self._history.add_friend_to_db(tox_id)
            try:
                alias = filter(lambda x: x[0] == tox_id, aliases)[0][1]
            except:
                alias = ''
            item = self.create_friend_item()
            name = alias or tox.friend_get_name(i) or tox_id
            status_message = tox.friend_get_status_message(i)
            message_getter = self._history.messages_getter(tox_id)
            friend = Friend(message_getter, i, name, status_message, item, tox_id)
            friend.set_alias(alias)
            self._friends.append(friend)
        self.filtration(self._show_online)

    # -----------------------------------------------------------------------------------------------------------------
    # Edit current user's data
    # -----------------------------------------------------------------------------------------------------------------

    def change_status(self):
        """
        Changes status of user (online, away, busy)
        """
        if self._status is not None:
            status = (self._status + 1) % 3
            super(self.__class__, self).set_status(status)
            self._tox.self_set_status(status)

    def set_name(self, value):
        super(self.__class__, self).set_name(value)
        self._tox.self_set_name(self._name.encode('utf-8'))

    def set_status_message(self, value):
        super(self.__class__, self).set_status_message(value)
        self._tox.self_set_status_message(self._status_message.encode('utf-8'))

    # -----------------------------------------------------------------------------------------------------------------
    # Filtration
    # -----------------------------------------------------------------------------------------------------------------

    def filtration(self, show_online=True, filter_str=''):
        """
        Filtration of friends list
        :param show_online: show online only contacts
        :param filter_str: show contacts which name contains this substring
        """
        filter_str = filter_str.lower()
        for index, friend in enumerate(self._friends):
            friend.visibility = (friend.status is not None or not show_online) and (filter_str in friend.name.lower())
            if friend.visibility:
                self._screen.friends_list.item(index).setSizeHint(QtCore.QSize(250, 70))
            else:
                self._screen.friends_list.item(index).setSizeHint(QtCore.QSize(250, 0))
        self._show_online, self._filter_string = show_online, filter_str
        settings = Settings.get_instance()
        settings['show_online_friends'] = self._show_online
        settings.save()

    def update_filtration(self):
        """
        Update list of contacts when 1 of friends change connection status
        """
        self.filtration(self._show_online, self._filter_string)

    def get_friend_by_number(self, num):
        return filter(lambda x: x.number == num, self._friends)[0]

    # -----------------------------------------------------------------------------------------------------------------
    # Work with active friend
    # -----------------------------------------------------------------------------------------------------------------

    def get_active(self):
        return self._active_friend

    def set_active(self, value=None):
        """
        :param value: number of new active friend in friend's list or None to update active user's data
        """
        # TODO: check if call started
        if value is None and self._active_friend == -1:  # nothing to update
            return
        if value == self._active_friend:
            return
        if value == -1:  # all friends were deleted
            self._screen.account_name.setText('')
            self._screen.account_status.setText('')
            self._active_friend = -1
            self._screen.account_avatar.setHidden(True)
            self._messages.clear()
            self._screen.messageEdit.clear()
            return
        try:
            if value is not None:
                self._active_friend = value
                friend = self._friends[value]
                self._friends[self._active_friend].set_messages(False)
                self._screen.messageEdit.clear()
                self._messages.clear()
                friend.load_corr()
                messages = friend.get_corr()[-PAGE_SIZE:]
                for message in messages:
                    if message.get_type() <= 1:
                        data = message.get_data()
                        self.create_message_item(data[0],
                                                 convert_time(data[2]),
                                                 friend.name if data[1] else self._name,
                                                 data[3])
                    elif message.get_type() == 2:
                        item = self.create_file_transfer_item(message)
                        if message.get_status() in (2, 4):  # active file transfer
                            ft = self._file_transfers[(message.get_friend_number(), message.get_file_number())]
                            ft.set_state_changed_handler(item.update)
                self._messages.scrollToBottom()
            else:
                friend = self._friends[self._active_friend]

            self._screen.account_name.setText(friend.name)
            self._screen.account_status.setText(friend.status_message)
            avatar_path = (Settings.get_default_path() + 'avatars/{}.png').format(friend.tox_id[:TOX_PUBLIC_KEY_SIZE * 2])
            if not os.path.isfile(avatar_path):  # load default image
                avatar_path = curr_directory() + '/images/avatar.png'
            pixmap = QtGui.QPixmap(QtCore.QSize(64, 64))
            pixmap.load(avatar_path)
            self._screen.account_avatar.setScaledContents(False)
            self._screen.account_avatar.setPixmap(pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio))
            self._screen.account_avatar.repaint()
        except:  # no friend found. ignore
            log('Incorrect friend value: ' + str(value))
            raise

    active_friend = property(get_active, set_active)

    def get_last_message(self):
        return self._friends[self._active_friend].get_last_message()

    def get_active_number(self):
        return self._friends[self._active_friend].number if self._active_friend + 1 else -1

    def get_active_name(self):
        return self._friends[self._active_friend].name if self._active_friend + 1 else ''

    def is_active_online(self):
        return self._active_friend + 1 and self._friends[self._active_friend].status is not None

    # -----------------------------------------------------------------------------------------------------------------
    # Private messages
    # -----------------------------------------------------------------------------------------------------------------

    def split_and_send(self, number, message_type, message):
        """
        Message splitting
        :param number: friend's number
        :param message_type: type of message
        :param message: message text
        """
        while len(message) > TOX_MAX_MESSAGE_LENGTH:
            size = TOX_MAX_MESSAGE_LENGTH * 4 / 5
            last_part = message[size:TOX_MAX_MESSAGE_LENGTH]
            if ' ' in last_part:
                index = last_part.index(' ')
            elif ',' in last_part:
                index = last_part.index(',')
            elif '.' in last_part:
                index = last_part.index('.')
            else:
                index = TOX_MAX_MESSAGE_LENGTH - size
            index += size + 1
            self._tox.friend_send_message(number, message_type, message[:index])
            message = message[index:]
        self._tox.friend_send_message(number, message_type, message)

    def new_message(self, friend_num, message_type, message):
        """
        Current user gets new message
        :param friend_num: friend_num of friend who sent message
        :param message_type: message type - plain text or action message (/me)
        :param message: text of message
        """
        if friend_num == self.get_active_number():  # add message to list
            user_name = Profile.get_instance().get_active_name()
            self.create_message_item(message.decode('utf-8'), curr_time(), user_name, message_type)
            self._messages.scrollToBottom()
            self._friends[self._active_friend].append_message(
                TextMessage(message.decode('utf-8'), MESSAGE_OWNER['FRIEND'], time.time(), message_type))
        else:
            friend = self.get_friend_by_number(friend_num)
            friend.set_messages(True)
            friend.append_message(
                TextMessage(message.decode('utf-8'), MESSAGE_OWNER['FRIEND'], time.time(), message_type))

    def send_message(self, text):
        """
        Send message to active friend
        :param text: message text
        """
        if self.is_active_online() and text:
            if text.startswith('/me '):
                message_type = TOX_MESSAGE_TYPE['ACTION']
                text = text[4:]
            else:
                message_type = TOX_MESSAGE_TYPE['NORMAL']
            friend = self._friends[self._active_friend]
            self.split_and_send(friend.number, message_type, text.encode('utf-8'))
            self.create_message_item(text, curr_time(), self._name, message_type)
            self._screen.messageEdit.clear()
            self._messages.scrollToBottom()
            friend.append_message(TextMessage(text, MESSAGE_OWNER['ME'], time.time(), message_type))

    # -----------------------------------------------------------------------------------------------------------------
    # History support
    # -----------------------------------------------------------------------------------------------------------------

    def save_history(self):
        """
        Save history to db
        """
        if hasattr(self, '_history'):
            if Settings.get_instance()['save_history']:
                for friend in self._friends:
                    messages = friend.get_corr_for_saving()
                    if not self._history.friend_exists_in_db(friend.tox_id):
                        self._history.add_friend_to_db(friend.tox_id)
                    self._history.save_messages_to_db(friend.tox_id, messages)
            del self._history

    def clear_history(self, num=None):
        if num is not None:
            friend = self._friends[num]
            friend.clear_corr()
            if self._history.friend_exists_in_db(friend.tox_id):
                self._history.delete_messages(friend.tox_id)
                self._history.delete_friend_from_db(friend.tox_id)
        else:  # clear all history
            for number in xrange(len(self._friends)):
                self.clear_history(number)
        if num is None or num == self.get_active_number():
            self._messages.clear()
            self._messages.repaint()

    def load_history(self):
        """
        Tries to load next part of messages
        """
        friend = self._friends[self._active_friend]
        friend.load_corr(False)
        data = friend.get_corr()
        if not data:
            return
        data.reverse()
        data = data[self._messages.count():self._messages.count() + PAGE_SIZE]
        for message in data:
            if message.get_type() <= 1:
                data = message.get_data()
                self.create_message_item(data[0],
                                         convert_time(data[2]),
                                         friend.name if data[1] else self._name,
                                         data[3],
                                         False)
            elif message.get_type() == 2:
                item = self.create_file_transfer_item(message, False)
                if message.get_status() in (2, 4):
                    ft = self._file_transfers[(message.get_friend_number(), message.get_file_number())]
                    ft.set_state_changed_handler(item.update)

    def export_history(self, directory):
        self._history.export(directory)

    # -----------------------------------------------------------------------------------------------------------------
    # Factories for friend, message and file transfer items
    # -----------------------------------------------------------------------------------------------------------------

    def create_friend_item(self):
        """
        Method-factory
        :return: new widget for friend instance
        """
        item = ContactItem()
        elem = QtGui.QListWidgetItem(self._screen.friends_list)
        elem.setSizeHint(QtCore.QSize(250, 70))
        self._screen.friends_list.addItem(elem)
        self._screen.friends_list.setItemWidget(elem, item)
        return item

    def create_message_item(self, text, time, name, message_type, append=True):
        item = MessageItem(text, time, name, message_type, self._messages)
        elem = QtGui.QListWidgetItem()
        elem.setSizeHint(QtCore.QSize(self._messages.width(), item.height()))
        if append:
            self._messages.addItem(elem)
        else:
            self._messages.insertItem(0, elem)
        self._messages.setItemWidget(elem, item)
        self._messages.repaint()

    def create_file_transfer_item(self, tm, append=True):
        data = list(tm.get_data())
        data[3] = self.get_friend_by_number(data[4]).name if data[3] else self._name
        item = FileTransferItem(*data)
        elem = QtGui.QListWidgetItem()
        elem.setSizeHint(QtCore.QSize(600, 50))
        if append:
            self._messages.addItem(elem)
        else:
            self._messages.insertItem(0, elem)
        self._messages.setItemWidget(elem, item)
        self._messages.repaint()
        return item

    # -----------------------------------------------------------------------------------------------------------------
    # Work with friends (remove, set alias, get public key)
    # -----------------------------------------------------------------------------------------------------------------

    def set_alias(self, num):
        friend = self._friends[num]
        name = friend.name.encode('utf-8')
        dialog = "Enter new alias for friend " + name.decode('utf-8') + "  or leave empty to use friend's name:"
        text, ok = QtGui.QInputDialog.getText(None, 'Set alias', dialog)
        if ok:
            settings = Settings.get_instance()
            aliases = settings['friends_aliases']
            if text:
                friend.name = text.encode('utf-8')
                try:
                    index = map(lambda x: x[0], aliases).index(friend.tox_id)
                    aliases[index] = (friend.tox_id, text)
                except:
                    aliases.append((friend.tox_id, text))
                friend.set_alias(text)
            else:  # use default name
                friend.name = self._tox.friend_get_name(friend.number).encode('utf-8')
                friend.set_alias('')
                try:
                    index = map(lambda x: x[0], aliases).index(friend.tox_id)
                    del aliases[index]
                except:
                    pass
            settings.save()
            self.set_active()

    def friend_public_key(self, num):
        return self._friends[num].tox_id

    def delete_friend(self, num):
        """
        Removes friend from contact list
        :param num: number of friend in list
        """
        friend = self._friends[num]
        self.clear_history(num)
        if self._history.friend_exists_in_db(friend.tox_id):
            self._history.delete_friend_from_db(friend.tox_id)
        self._tox.friend_delete(friend.number)
        del self._friends[num]
        self._screen.friends_list.takeItem(num)
        if num == self._active_friend:  # active friend was deleted
            if not len(self._friends):  # last friend was deleted
                self.set_active(-1)
            else:
                self.set_active(0)

    # -----------------------------------------------------------------------------------------------------------------
    # Friend requests
    # -----------------------------------------------------------------------------------------------------------------

    def send_friend_request(self, tox_id, message):
        """
        Function tries to send request to contact with specified id
        :param tox_id: id of new contact or tox dns 4 value
        :param message: additional message
        :return: True on success else error string
        """
        try:
            message = message or 'Add me to your contact list'
            if '@' in tox_id:  # value like groupbot@toxme.io
                tox_id = tox_dns(tox_id)
                if tox_id is None:
                    raise Exception('TOX DNS lookup failed')
            result = self._tox.friend_add(tox_id, message.encode('utf-8'))
            tox_id = tox_id[:TOX_PUBLIC_KEY_SIZE * 2]
            item = self.create_friend_item()
            if not self._history.friend_exists_in_db(tox_id):
                self._history.add_friend_to_db(tox_id)
            message_getter = self._history.messages_getter(tox_id)
            friend = Friend(message_getter, result, tox_id, '', item, tox_id)
            self._friends.append(friend)
            return True
        except Exception as ex:  # wrong data
            log('Friend request failed with ' + str(ex))
            return str(ex)

    def process_friend_request(self, tox_id, message):
        """
        Accept or ignore friend request
        :param tox_id: tox id of contact
        :param message: message
        """
        try:
            text = QtGui.QApplication.translate('MainWindow', 'User {} wants to add you to contact list. Message:\n{}', None, QtGui.QApplication.UnicodeUTF8)
            info = text.format(tox_id, message)
            fr_req = QtGui.QApplication.translate('MainWindow', 'Friend request', None, QtGui.QApplication.UnicodeUTF8)
            reply = QtGui.QMessageBox.question(None, fr_req, info, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:  # accepted
                num = self._tox.friend_add_norequest(tox_id)  # num - friend number
                item = self.create_friend_item()
                if not self._history.friend_exists_in_db(tox_id):
                    self._history.add_friend_to_db(tox_id)
                if not self._history.friend_exists_in_db(tox_id):
                    self._history.add_friend_to_db(tox_id)
                message_getter = self._history.messages_getter(tox_id)
                friend = Friend(message_getter, num, tox_id, '', item, tox_id)
                self._friends.append(friend)
        except Exception as ex:  # something is wrong
            log('Accept friend request failed! ' + str(ex))

    # -----------------------------------------------------------------------------------------------------------------
    # Reset
    # -----------------------------------------------------------------------------------------------------------------

    def reset(self, restart):
        """
        Recreate tox instance
        :param restart: method which calls restart and returns new tox instance
        """
        for key in self._file_transfers.keys():
            self._file_transfers[key].cancel()
            del self._file_transfers[key]
        del self._tox
        self._tox = restart()
        self.status = None
        for friend in self._friends:
            friend.status = None

    def close(self):
        self._call.stop()
        del self._call

    # -----------------------------------------------------------------------------------------------------------------
    # File transfers support
    # -----------------------------------------------------------------------------------------------------------------

    def incoming_file_transfer(self, friend_number, file_number, size, file_name):
        """
        New transfer
        :param friend_number: number of friend who sent file
        :param file_number: file number
        :param size: file size in bytes
        :param file_name: file name without path
        """
        settings = Settings.get_instance()
        friend = self.get_friend_by_number(friend_number)
        file_name = file_name.decode('utf-8')
        if settings['allow_auto_accept'] and friend.tox_id in settings['auto_accept_from_friends']:
            path = settings['auto_accept_path'] or curr_directory()
            new_file_name, i = file_name, 1
            while os.path.isfile(path + '/' + new_file_name):  # file with same name already exists
                if '.' in file_name:  # has extension
                    d = file_name.rindex('.')
                else:  # no extension
                    d = len(file_name)
                new_file_name = file_name[:d] + ' ({})'.format(i) + file_name[d:]
                i += 1
            self.accept_transfer(None, path + '/' + new_file_name, friend_number, file_number)
            tm = TransferMessage(MESSAGE_OWNER['FRIEND'],
                                 time.time(),
                                 FILE_TRANSFER_MESSAGE_STATUS['INCOMING_STARTED'],
                                 size,
                                 new_file_name,
                                 friend_number,
                                 file_number)
        else:
            tm = TransferMessage(MESSAGE_OWNER['FRIEND'],
                                 time.time(),
                                 FILE_TRANSFER_MESSAGE_STATUS['INCOMING_NOT_STARTED'],
                                 size,
                                 file_name,
                                 friend_number,
                                 file_number)
        if friend_number == self.get_active_number():
            self.create_file_transfer_item(tm)
            self._messages.scrollToBottom()
        else:
            friend.set_messages(True)
        friend.append_message(tm)

    def cancel_transfer(self, friend_number, file_number, already_cancelled=False):
        """
        Stop transfer
        :param friend_number: number of friend
        :param file_number: file number
        :param already_cancelled: was cancelled by friend
        """
        if (friend_number, file_number) in self._file_transfers:
            tr = self._file_transfers[(friend_number, file_number)]
            if not already_cancelled:
                tr.cancel()
            else:
                tr.cancelled()
            del self._file_transfers[(friend_number, file_number)]
        else:
            self._tox.file_control(friend_number, file_number, TOX_FILE_CONTROL['CANCEL'])
        self.get_friend_by_number(friend_number).update_transfer_data(file_number,
                                                                      FILE_TRANSFER_MESSAGE_STATUS['CANCELLED'])

    def accept_transfer(self, item, path, friend_number, file_number, size):
        """
        :param item: transfer item
        :param path: path for saving
        :param friend_number: friend number
        :param file_number: file number
        :param size: file size
        """
        rt = ReceiveTransfer(path, self._tox, friend_number, size, file_number)
        self._file_transfers[(friend_number, file_number)] = rt
        self._tox.file_control(friend_number, file_number, TOX_FILE_CONTROL['RESUME'])
        if item is not None:
            rt.set_state_changed_handler(item.update)
        self.get_friend_by_number(friend_number).update_transfer_data(file_number, FILE_TRANSFER_MESSAGE_STATUS['INCOMING_STARTED'])

    def send_screenshot(self, data):
        """
        Send screenshot to current active friend
        :param data: raw data - png
        """
        friend = self._friends[self._active_friend]
        st = SendFromBuffer(self._tox, friend.number, data, 'toxygen_inline.png')
        self._file_transfers[(friend.number, st.get_file_number())] = st
        tm = TransferMessage(MESSAGE_OWNER['ME'],
                             time.time(),
                             FILE_TRANSFER_MESSAGE_STATUS['OUTGOING'],
                             len(data),
                             'toxygen_inline.png',
                             friend.number,
                             st.get_file_number())
        item = self.create_file_transfer_item(tm)
        friend.append_message(tm)
        st.set_state_changed_handler(item.update)
        self._messages.scrollToBottom()

    def send_file(self, path):
        """
        Send file to current active friend
        :param path: file path
        """
        friend_number = self.get_active_number()
        st = SendTransfer(path, self._tox, friend_number)
        self._file_transfers[(friend_number, st.get_file_number())] = st
        tm = TransferMessage(MESSAGE_OWNER['ME'],
                             time.time(),
                             FILE_TRANSFER_MESSAGE_STATUS['OUTGOING'],
                             os.path.getsize(path),
                             os.path.basename(path),
                             friend_number,
                             st.get_file_number())
        item = self.create_file_transfer_item(tm)
        st.set_state_changed_handler(item.update)
        self._friends[self._active_friend].append_message(tm)
        self._messages.scrollToBottom()

    def incoming_chunk(self, friend_number, file_number, position, data):
        if (friend_number, file_number) in self._file_transfers:
            transfer = self._file_transfers[(friend_number, file_number)]
            transfer.write_chunk(position, data)
            if transfer.state:
                if type(transfer) is ReceiveAvatar:
                    self.get_friend_by_number(friend_number).load_avatar()
                    self.set_active(None)
                else:
                    self.get_friend_by_number(friend_number).update_transfer_data(file_number, FILE_TRANSFER_MESSAGE_STATUS['FINISHED'])
                del self._file_transfers[(friend_number, file_number)]

    def outgoing_chunk(self, friend_number, file_number, position, size):
        if (friend_number, file_number) in self._file_transfers:
            transfer = self._file_transfers[(friend_number, file_number)]
            transfer.send_chunk(position, size)
            if transfer.state:
                del self._file_transfers[(friend_number, file_number)]
                if type(transfer) is not SendAvatar:
                    self.get_friend_by_number(friend_number).update_transfer_data(file_number, FILE_TRANSFER_MESSAGE_STATUS['FINISHED'])

    # -----------------------------------------------------------------------------------------------------------------
    # Avatars support
    # -----------------------------------------------------------------------------------------------------------------

    def send_avatar(self, friend_number):
        """
        :param friend_number: number of friend who should get new avatar
        """
        avatar_path = (ProfileHelper.get_path() + 'avatars/{}.png').format(self._tox_id[:TOX_PUBLIC_KEY_SIZE * 2])
        if not os.path.isfile(avatar_path):  # reset image
            avatar_path = None
        sa = SendAvatar(avatar_path, self._tox, friend_number)
        self._file_transfers[(friend_number, sa.get_file_number())] = sa

    def incoming_avatar(self, friend_number, file_number, size):
        """
        Friend changed avatar
        :param friend_number: friend number
        :param file_number: file number
        :param size: size of avatar or 0 (default avatar)
        """
        ra = ReceiveAvatar(self._tox, friend_number, size, file_number)
        if ra.state != TOX_FILE_TRANSFER_STATE['CANCELED']:
            self._file_transfers[(friend_number, file_number)] = ra
        else:
            self.get_friend_by_number(friend_number).load_avatar()
            if self.get_active_number() == friend_number:
                self.set_active(None)

    def reset_avatar(self):
        super(Profile, self).reset_avatar()
        for friend in filter(lambda x: x.status is not None, self._friends):
            self.send_avatar(friend.number)

    def set_avatar(self, data):
        super(Profile, self).set_avatar(data)
        for friend in filter(lambda x: x.status is not None, self._friends):
            self.send_avatar(friend.number)

    # -----------------------------------------------------------------------------------------------------------------
    # AV support
    # -----------------------------------------------------------------------------------------------------------------

    def get_call(self):
        return self._call

    call_data = property(get_call)

    # TODO: move to calls.py?

    def call(self, audio):
        num = self.get_active_number()
        if num not in self._call:  # start call
            self._call(num)
            self._screen.active_call()
        else:  # finish or cancel call if you call with active friend
            self.stop_call(False)

    def incoming_call(self, audio, video, friend_number):
        friend = self.get_friend_by_number(friend_number)
        if friend_number == self.get_active_number():
            self._screen.incoming_call()
            self._call.toxav_call_cb(friend_number, audio, video)
        else:
            friend.set_messages(True)
        if video:
            text = QtGui.QApplication.translate("incoming_call", "Incoming video call", None, QtGui.QApplication.UnicodeUTF8)
        else:
            text = QtGui.QApplication.translate("incoming_call", "Incoming audio call", None, QtGui.QApplication.UnicodeUTF8)
        self._call_widget = avwidgets.IncomingCallWidget(friend_number, text, friend.name)
        self._call_widget.set_pixmap(ProfileHelper.get_path() + 'avatars/{}.png'.format(friend.tox_id))
        self._call_widget.show()

    def start_call(self, friend_number, audio, video):
        pass

    def stop_call(self, friend_number, by_friend):
        if not self._call:
            return
        self._screen.call_finished()


def tox_factory(data=None, settings=None):
    """
    :param data: user data from .tox file. None = no saved data, create new profile
    :param settings: current application settings. None = defaults settings will be used
    :return: new tox instance
    """
    if settings is None:
        settings = Settings.get_default_settings()
    tox_options = Tox.options_new()
    tox_options.contents.udp_enabled = settings['udp_enabled']
    tox_options.contents.proxy_type = settings['proxy_type']
    tox_options.contents.proxy_host = settings['proxy_host']
    tox_options.contents.proxy_port = settings['proxy_port']
    tox_options.contents.start_port = settings['start_port']
    tox_options.contents.end_port = settings['end_port']
    tox_options.contents.tcp_port = settings['tcp_port']
    if data:  # load existing profile
        tox_options.contents.savedata_type = TOX_SAVEDATA_TYPE['TOX_SAVE']
        tox_options.contents.savedata_data = c_char_p(data)
        tox_options.contents.savedata_length = len(data)
    else:  # create new profile
        tox_options.contents.savedata_type = TOX_SAVEDATA_TYPE['NONE']
        tox_options.contents.savedata_data = None
        tox_options.contents.savedata_length = 0
    return Tox(tox_options)
