import wx
import subprocess
import os

SETTINGS_FILE = "src/last_settings.txt"


class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Voice Monitor", size = (800,450))
        panel = wx.Panel(self)
        
        # Create "Monitor" button
        self.monitor_button = wx.Button(panel, label="Monitor", pos= (540,280))
        self.monitor_button.Bind(wx.EVT_BUTTON, self.on_monitor)
        
        # Create "Test" button
        self.test_button = wx.Button(panel, label= "Mic Test", pos= (620,280))
        self.test_button.Bind(wx.EVT_BUTTON, self.on_test)
        
        
        # Static Instruction TXT
        self.instruction_static_text_01 = wx.StaticText(panel, pos=(50, 20), label="Enter Pitch as whole number between 50-350")
        self.instruction_static_text_02 = wx.StaticText(panel, pos=(50, 150), label="Optional Features")
        
        
        # set Pitch range (low pass)
        self.instruction_static_text_max = wx.StaticText(panel, pos=(50, 50), label="Maximum:")
        self.custom_text_ctrl_max = wx.TextCtrl(panel, pos=(120,50), size=(50, -1), style=wx.TE_PROCESS_ENTER)
        self.custom_text_ctrl_max.Bind(wx.EVT_CHAR, self.onChar)
        
        # set Pitch range (high pass)
        self.instruction_static_text_min = wx.StaticText(panel, pos=(50, 100), label="Minimum:")
        self.custom_text_ctrl_min = wx.TextCtrl(panel, pos=(120,100), size=(50, -1), style=wx.TE_PROCESS_ENTER)
        self.custom_text_ctrl_min.Bind(wx.EVT_CHAR, self.onChar)
        
        # Feature Menu
            # Play "pin-pon" (pin-pon.mp3) noise when a sentence is completed without 'error'
        self.checkbox_sentence_monitor = wx.CheckBox(panel, label="Sentence Observation", pos=(100, 180))
        
            # Play a "bad noise" (error.mp3) when audio input is outside of range 
        self.checkbox_out_of_range = wx.CheckBox(panel, label="Outside target range notification", pos=(350, 180))
        
            # Mute mic when audio is outside of range
        self.checkbox_self_mute = wx.CheckBox(panel, label="Mute mic when outside of range", pos=(100, 230))
            
            # Monitor audio input resonance
        self.checkbox_resonance = wx.CheckBox(panel, label="Resonance monitor", pos=(350, 230))
        
            # Score system (every minute a text file with score is updated as a percentage (minutes inside range) / (minutes of mic input)
        self.checkbox_score = wx.CheckBox(panel, label="Calculate a score for the session", pos=(100, 280))
        
        
        
        self.load_settings() # If available
        self.Show()
        
        
    def save_settings(self):
        """
        Save current settings to last_settings.txt
        """
        settings = {
            "max": self.custom_text_ctrl_max.GetValue(),
            "min": self.custom_text_ctrl_min.GetValue(),
            "sentence_monitor": self.checkbox_sentence_monitor.GetValue(),
            "out_of_range": self.checkbox_out_of_range.GetValue(),
            "self_mute": self.checkbox_self_mute.GetValue(),
            "resonance": self.checkbox_resonance.GetValue(),
            "score": self.checkbox_score.GetValue()
        }

        try:
            with open(SETTINGS_FILE, "w") as f:
                for key, value in settings.items():
                    f.write(f"{key}:{value}\n")
        except Exception as e:
            wx.LogError(f"Error saving settings: {e}")
            

            
    def load_settings(self):
        """
        Load settings from last_settings.txt if exists
        """
        if not os.path.exists(SETTINGS_FILE):
            return

        try:
            with open(SETTINGS_FILE, "r") as f:
                lines = f.readlines()
        except Exception as e:
            wx.LogError(f"Error reading settings: {e}")
            return

        settings = {}
        for line in lines:
            if ":" in line:
                key, value = line.strip().split(":", 1)
                settings[key] = value

        # Restore values if present
        self.custom_text_ctrl_max.SetValue(settings.get("max", ""))
        self.custom_text_ctrl_min.SetValue(settings.get("min", ""))
        def str_to_bool(s):
            return s.lower() == "true"
        self.checkbox_sentence_monitor.SetValue(str_to_bool(settings.get("sentence_monitor", "False")))
        self.checkbox_out_of_range.SetValue(str_to_bool(settings.get("out_of_range", "False")))
        self.checkbox_self_mute.SetValue(str_to_bool(settings.get("self_mute", "False")))
        self.checkbox_resonance.SetValue(str_to_bool(settings.get("resonance", "False")))
        self.checkbox_score.SetValue(str_to_bool(settings.get("score", "False")))


    def on_monitor(self, event):
        max_pitch = self.custom_text_ctrl_max.GetValue()
        min_pitch = self.custom_text_ctrl_min.GetValue()
        self.save_settings()
        # Build argument list
        cmd = [
            "python", "src/Monitor.py",
            "--max", str(max_pitch),
            "--min", str(min_pitch),
        ]
        # Append flags if box is checked
        if self.checkbox_sentence_monitor.GetValue():
            cmd.append("--sentence-monitor")
        if self.checkbox_out_of_range.GetValue():
            cmd.append("--out-of-range")
        if self.checkbox_self_mute.GetValue():
            cmd.append("--self-mute")
        if self.checkbox_resonance.GetValue():
            cmd.append("--resonance")
        if self.checkbox_score.GetValue():
            cmd.append("--score")

        # Launch Monitor.py as a detached process
        subprocess.Popen(cmd)
        
    def on_test(self, event):
        cmd = [ "python", "test.py"]
        subprocess.Popen(cmd)
        
    def onChar(self, event):
        key = event.GetKeyCode()
        try:
            character = chr(key)
        except ValueError:
            character = ""
        acceptable_keys = (
            key in (wx.WXK_BACK, wx.WXK_DELETE, wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_RETURN)
        )
        if character.isdigit() or acceptable_keys:
            # Get current value of the TextCtrl
            ctrl = event.GetEventObject()
            current_value = ctrl.GetValue()
            insertion_point = ctrl.GetInsertionPoint()
            # Simulate what the new value would be if this key is accepted
            if key in (wx.WXK_BACK, wx.WXK_DELETE):
                # Backspace or delete – allow
                event.Skip()
                return
            # Simulate inserting the new character
            new_value = current_value[:insertion_point] + character + current_value[insertion_point:]
            if new_value == "":
                event.Skip()
                return
            try:
                if 0 <= int(new_value) <= 999:
                    event.Skip()
                else:
                    wx.Bell()
                    return  # Block
            except ValueError:
                wx.Bell()
                return  # Block
        else:
            wx.Bell()
            return  # Block
        
if __name__ == "__main__":
    app = wx.App(False)
    frame = MyFrame()
    app.MainLoop()
