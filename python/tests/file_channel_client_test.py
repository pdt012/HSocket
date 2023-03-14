# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
from src.hsocket.hclient import HTcpChannelClient
from tests.file_client_test import file_test


if __name__ == '__main__':
    channel_client = HTcpChannelClient()
    file_test(channel_client)
    input("press enter to exit")
