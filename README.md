# Gomoku-With-Robot-Arm
This is my university project, it's simple but can work.

The training code is modified from https://github.com/junxiaosong/AlphaZero_Gomoku, I add some functions inside:

1. If training interrupted, run the training code again will lode the saved data.
2. Allow pure_mcts_playout_num grows up to 10000. (original 5000)
3. Can let n_playout grow up, but I am not sure this is useful or not.

# How to play
This code may not work correctly on your PC because I am not a professional in this area, and I have no time optimize  them. 
To make this project work, here's somethings that you can do:

1. If you just want to play on CMD:
    Just run "./ESGomoku/human_play.py", it's almost the same to the original code.
2. If you want to play in Unity:
    (Win10 only) Open "./Unity/ESGomoku" folder in Unity Editor v2019.4.3f1 (Yes, I hadn't built it.), and press "Play" button in editor.
3. Play with Robot arm(not recommended because it's complicated):
    You need a "Tinkerkit Braccio" robot arm, and connect to your PC.
    Then, fix the "./ESGomoku/braccio_player.py", and change the variable "Global.port" to your usb port.
    **Fix** and run "./ESGomoku/Play_With_Robot.py" if you don't need the GUI, or run "./ESGomoku/main.py" to activate the GUI.

# Where to change the model?
Just change the file "best_model_9_9_5.h5" in "./ESGomoku", this is the keras AI model. 

# How to train
Run "./TriainModel-9_9_5/train.py"