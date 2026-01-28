
import paramiko
import os
from dotenv import load_dotenv

load_dotenv('/home/carag/.camspy_env')
username = os.getenv('SF_USER')
password = os.getenv('SF_PASS')
hostname = '192.168.50.170'
port = 8322

# Create an SSH client
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(hostname, port, username, password)
# Create an SFTP session
sftp = ssh_client.open_sftp()

v = '#1-test_cam-2026-01-27_21-43-43.mp4'
local_file = '/home/carag/camspy/video2/' + v
remote_file = '/volume1/icipher/pi_video_test/T' + v
sftp.put(local_file, remote_file)

