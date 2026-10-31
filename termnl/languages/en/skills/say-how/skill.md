---
does: check mood
label: say how the board is doing
reads: feeling
admin: no
approve: no
topic: You and me
---

Small talk (Gab, 30 Oct: "hey, how are you doing? Or, hey, what's your day?" and "I think it's cool that he
says, hey, I'm doing fine, I'm 41 degrees centigrade and up for 3 days. I still have 52 gig free"). The board
answers for itself, in a sentence: the health check without its table (check the board has the table).

## Words

- mood: mood

## People say

- (hey) how are you (doing)
- (hey) how's it going
- (hey) how's your day

## Also said

- how are you
- how are you doing
- hey how are you
- how's it going
- how's your day
- what's your day
- how are you today

## When it's fine

- I'm doing fine, {user}: {@sys.feeling.temperature}, up for {@sys.feeling.uptime}, and I still have {@sys.feeling.free} free.
- All good, {user}. I'm at {@sys.feeling.temperature}, up for {@sys.feeling.uptime}, {@sys.feeling.free} free.
- Fine, thanks {user}! {@sys.feeling.temperature}, running for {@sys.feeling.uptime}, {@sys.feeling.free} still free.
- Doing well, {user}: {@sys.feeling.temperature} and up for {@sys.feeling.uptime}. {@sys.feeling.free} free on the disk.

## When it's busy

- A bit busy, {user}: {@sys.feeling.temperature}, up for {@sys.feeling.uptime}, {@sys.feeling.free} free.
- I'm working hard, {user}: {@sys.feeling.temperature}, memory at {@sys.feeling.memory}, {@sys.feeling.free} free.
- Busy but fine, {user}. {@sys.feeling.temperature}, up for {@sys.feeling.uptime}, {@sys.feeling.free} free.
- Keeping up, {user}: {@sys.feeling.temperature}, the disk {@sys.feeling.disk} full, memory at {@sys.feeling.memory}.

## When it's struggling

- Not great, {user}: {@sys.feeling.temperature}, memory at {@sys.feeling.memory}, only {@sys.feeling.free} free. Ask me to check the board.
- I'm struggling, {user}: {@sys.feeling.temperature}, the disk {@sys.feeling.disk} full. Ask me to check the board.
- Could be better, {user}: {@sys.feeling.temperature}, {@sys.feeling.free} free, memory at {@sys.feeling.memory}. Ask me to check the board.
- Not my best day, {user}: {@sys.feeling.temperature}, memory at {@sys.feeling.memory}, the disk {@sys.feeling.disk} full. Ask me to check the board.
