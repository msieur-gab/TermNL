---
does: check music
label: say what's playing
admin: no
approve: no
---

Gab, on the board, 23 Oct: "play some music", "next", then "what is that song", which skipped to the next one.

## People say

- what is (that/this) (song/track)
- what's (that/this) (song/track)
- what is playing (now/right now)
- what's playing (now/right now)
- what are you playing (now/right now)
- which song/track is (this/that/playing)
- what song/track is (this/that/playing)

## Also said

- what is that song
- what's this song
- what song is this
- which track is playing
- what's playing
- what are you playing right now
- who is singing
- who's this artist
- what am I listening to
- tell me what's playing
- what's the name of this song
- I like this one, what is it called
- what's on right now
- which album is this from

## Command

mpc current -f '[[%artist% – ]%title%]|[%file%]' | grep . || echo nothing

## Replies

- done: Playing now: {output}.
