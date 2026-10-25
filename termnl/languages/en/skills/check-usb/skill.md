---
does: check usb
label: check what's plugged in
admin: no
approve: no
---

## People say

- is (my/the/a/an) usb plugged in
- what usb is plugged in
- check (the/my) usb

## Also said

- is my USB stick plugged in?
- do you see the SD card
- list the USB devices plugged into the board
- did the board pick up my external drive
- what sticks are in right now
- USB drives?
- I just put a memory card in, is it showing up

## Command

lsblk -o NAME,SIZE,TRAN,MOUNTPOINT

## Replies

- done: Drives and cards on the board: {output} | Here's what's plugged in: {output}
