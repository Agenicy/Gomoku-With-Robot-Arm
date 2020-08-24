from gtts import gTTS
import tempfile
from pygame import mixer
 
def say(text, filename=None):
    with tempfile.NamedTemporaryFile(delete=True) as temp:
        tts = gTTS(text, lang='zh-cn',slow=False)
        #tts = gTTS(text, lang='en',slow=False)
        if filename is None:
            filename = "{}.mp3".format(temp.name)
        tts.save(filename)
        mixer.init()
        mixer.music.load(filename)
        mixer.music.play()
        while mixer.music.get_busy() == True:
            continue
        mixer.quit()

say('遊戲開始，讓我聯絡一下我的手指', filename='game_start.mp3')
