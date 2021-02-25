# The MIT License (MIT)
# Copyright (c) 2019 Michael Shi
# Copyright (c) 2020 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:
# - read 32-bit audio samples from the left channel of an I2S microphone
# - snip upper 16-bits from each 32-bit microphone sample
# - write 16-bit samples to a SD card file using WAV format
#
# Recorded WAV file is named:
#   "mic_left_channel_16bits.wav"
#
# Hardware tested:
# - INMP441 microphone module 
# - MSM261S4030H0 microphone module

import uos
from machine import Pin
from machine import SDCard
from machine import I2S

#======= USER CONFIGURATION =======
RECORD_TIME_IN_SECONDS = 5
SAMPLE_RATE_IN_HZ = 22050
#======= USER CONFIGURATION =======

WAV_SAMPLE_SIZE_IN_BITS = 16
WAV_SAMPLE_SIZE_IN_BYTES = WAV_SAMPLE_SIZE_IN_BITS // 8
MIC_SAMPLE_BUFFER_SIZE_IN_BYTES = 4096
SDCARD_SAMPLE_BUFFER_SIZE_IN_BYTES = MIC_SAMPLE_BUFFER_SIZE_IN_BYTES // 2 # why divide by 2? only using 16-bits of 32-bit samples
NUM_SAMPLE_BYTES_TO_WRITE = RECORD_TIME_IN_SECONDS * SAMPLE_RATE_IN_HZ * WAV_SAMPLE_SIZE_IN_BYTES
NUM_SAMPLES_IN_DMA_BUFFER = 256
NUM_CHANNELS = 1

# snip_16_mono():  snip 16-bit samples from a 32-bit mono sample stream
# assumption: I2S configuration for mono microphone.  e.g. I2S channelformat = ONLY_LEFT or ONLY_RIGHT
# example snip:  
#   samples_in[] =  [0x44, 0x55, 0xAB, 0x77, 0x99, 0xBB, 0x11, 0x22]             
#   samples_out[] = [0xAB, 0x77, 0x11, 0x22]
#   notes:
#       samples_in[] arranged in little endian format:  
#           0x77 is the most significant byte of the 32-bit sample
#           0x44 is the least significant byte of the 32-bit sample
#
# returns:  number of bytes snipped
def snip_16_mono(samples_in, samples_out):
    num_samples = len(samples_in) // 4
    for i in range(num_samples):
        samples_out[2*i] = samples_in[4*i + 2]
        samples_out[2*i + 1] = samples_in[4*i + 3]
            
    return num_samples * 2

def create_wav_header(sampleRate, bitsPerSample, num_channels, num_samples):
    datasize = num_samples * num_channels * bitsPerSample // 8
    o = bytes("RIFF",'ascii')                                                   # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4,'little')                                   # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE",'ascii')                                                  # (4byte) File type
    o += bytes("fmt ",'ascii')                                                  # (4byte) Format Chunk Marker
    o += (16).to_bytes(4,'little')                                              # (4byte) Length of above format data
    o += (1).to_bytes(2,'little')                                               # (2byte) Format type (1 - PCM)
    o += (num_channels).to_bytes(2,'little')                                    # (2byte)
    o += (sampleRate).to_bytes(4,'little')                                      # (4byte)
    o += (sampleRate * num_channels * bitsPerSample // 8).to_bytes(4,'little')  # (4byte)
    o += (num_channels * bitsPerSample // 8).to_bytes(2,'little')               # (2byte)
    o += (bitsPerSample).to_bytes(2,'little')                                   # (2byte)
    o += bytes("data",'ascii')                                                  # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4,'little')                                        # (4byte) Data size in bytes
    return o

bck_pin = Pin(13)
ws_pin = Pin(14)
sdin_pin = Pin(34)

audio_in = I2S(
    I2S.NUM0, 
    bck=bck_pin, ws=ws_pin, sdin=sdin_pin,
    standard=I2S.PHILIPS, 
    mode=I2S.MASTER_RX,
    dataformat=I2S.B32,
    channelformat=I2S.ONLY_LEFT,
    samplerate=SAMPLE_RATE_IN_HZ,
    dmacount=50,
    dmalen=NUM_SAMPLES_IN_DMA_BUFFER
)

# configure SD card:
# See [docs](https://docs.micropython.org/en/latest/library/machine.SDCard.html#esp32) for
# recommended pins depending on the chosen slot.
#   slot=2 configures SD card to use the SPI3 controller (VSPI), DMA channel = 2
#   slot=3 configures SD card to use the SPI2 controller (HSPI), DMA channel = 1
sd = SDCard(slot=2, sck=Pin(18), mosi=Pin(23), miso=Pin(19), cs=Pin(5))
uos.mount(sd, "/sd")
wav = open('/sd/mic_left_channel_16bits.wav','wb')

# create header for WAV file and write to SD card
wav_header = create_wav_header(
    SAMPLE_RATE_IN_HZ, 
    WAV_SAMPLE_SIZE_IN_BITS, 
    NUM_CHANNELS, 
    SAMPLE_RATE_IN_HZ * RECORD_TIME_IN_SECONDS
)
num_bytes_written = wav.write(wav_header)

# allocate sample arrays
#   memoryview used to reduce heap allocation in while loop
mic_samples = bytearray(MIC_SAMPLE_BUFFER_SIZE_IN_BYTES)
mic_samples_mv = memoryview(mic_samples)
wav_samples = bytearray(SDCARD_SAMPLE_BUFFER_SIZE_IN_BYTES)
wav_samples_mv = memoryview(wav_samples)

num_sample_bytes_written_to_wav = 0

print('Starting')
# read 32-bit samples from I2S microphone, snip upper 16-bits, write snipped samples to WAV file
while num_sample_bytes_written_to_wav < NUM_SAMPLE_BYTES_TO_WRITE:
    try:
        # try to read a block of samples from the I2S microphone
        # readinto() method returns 0 if no DMA buffer is full
        num_bytes_read_from_mic = audio_in.readinto(mic_samples_mv, timeout=0)
        if num_bytes_read_from_mic > 0:
            # snip upper 16-bits from each 32-bit microphone sample
            num_bytes_snipped = snip_16_mono(mic_samples_mv[:num_bytes_read_from_mic], wav_samples_mv)
            num_bytes_to_write = min(num_bytes_snipped, NUM_SAMPLE_BYTES_TO_WRITE - num_sample_bytes_written_to_wav)
            # write samples to WAV file
            num_bytes_written = wav.write(wav_samples_mv[:num_bytes_to_write])
            num_sample_bytes_written_to_wav += num_bytes_written
    except (KeyboardInterrupt, Exception) as e:
        print('caught exception {} {}'.format(type(e).__name__, e))
        break

wav.close()
uos.umount("/sd")
sd.deinit()
audio_in.deinit()
print('Done')
print('%d sample bytes written to WAV file' % num_sample_bytes_written_to_wav)