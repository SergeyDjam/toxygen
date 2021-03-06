

MESSAGE_TYPE = {
    'TEXT': 0,
    'ACTION': 1,
    'FILE_TRANSFER': 2,
    'INLINE': 3
}

FILE_TRANSFER_MESSAGE_STATUS = {
    'FINISHED': 0,
    'CANCELLED': 1,
    'OUTGOING': 2,
    'INCOMING_NOT_STARTED': 3,
    'INCOMING_STARTED': 4
}


class Message(object):

    def __init__(self, message_type, owner, time):
        self._time = time
        self._type = message_type
        self._owner = owner

    def get_type(self):
        return self._type

    def get_owner(self):
        return self._owner


class TextMessage(Message):
    """
    Plain text or action message
    """

    def __init__(self, message, owner, time, message_type):
        super(TextMessage, self).__init__(message_type, owner, time)
        self._message = message

    def get_data(self):
        return self._message, self._owner, self._time, self._type


class TransferMessage(Message):
    """
    Message with info about file transfer
    """

    def __init__(self, owner, time, status, size, name, friend_number, file_number):
        super(TransferMessage, self).__init__(MESSAGE_TYPE['FILE_TRANSFER'], owner, time)
        self._status = status
        self._size = size
        self._file_name = name
        self._friend_number, self._file_number = friend_number, file_number

    def is_active(self, file_number):
        return self._file_number == file_number and self._status > 1

    def get_friend_number(self):
        return self._friend_number

    def get_file_number(self):
        return self._file_number

    def get_status(self):
        return self._status

    def set_status(self, value):
        self._status = value

    def get_data(self):
        return self._file_name, self._size, self._time, self._owner, self._friend_number, self._file_number, self._status


class InlineImage(Message):
    """
    Inline image
    """

    def __init__(self, data):
        super(InlineImage, self).__init__(MESSAGE_TYPE['INLINE'], None, None)
        self._data = data

    def get_data(self):
        return self._data
