import subprocess as sp
import re
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy_garden.mapview import MapView, MapMarkerPopup
from kivy.uix.screenmanager import ScreenManager, Screen
import socket
import pickle


# First page, where user types his name and joins the game
class LoginLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(LoginLayout, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 20
        name_label = Label(text="Name")
        self.name_box = TextInput(multiline=False)
        self.name_box.bind()
        join = Button(text="Join", on_press=lambda x: self.join_but())
        LoginLayout.add_widget(self, name_label)
        LoginLayout.add_widget(self, self.name_box)
        LoginLayout.add_widget(self, join)

    def join_but(self):
        game_app.name = self.name_box.text
        game_app.screen_manager.current = "Game"


# main page where playes can see each others and try to catch.
class GameLayout(BoxLayout):
    time = 10   # screen update time
    lat_value = 0
    lon_value = 0
    lat = NumericProperty(lat_value)
    lon = NumericProperty(lon_value)
    # server connection data
    HEADER = 4096
    PORT = 8080
    FORMAT = 'utf-8'
    DISCONNECT_MESSAGE = "!DISCONNECT"
    SERVER = "192.168.0.13"
    ADDR = (SERVER, PORT)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    # main screen widgets
    mapview = MapView(zoom=3, lat=lat_value, lon=lon_value, size_hint=(1, 3))
    role_label = Label(font_size='30sp')
    all_markers = []

    def __init__(self, **kwargs):
        super(GameLayout, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.mapview.map_source = "osm"
        self.mapview.double_tap_zoom = True
        GameLayout.add_widget(self, self.role_label)
        GameLayout.add_widget(self, self.mapview)

        marker = MapMarkerPopup()
        self.location()
        marker.lat = self.lat_value
        marker.lon = self.lon_value
        marker.source = "icons/8GKM3.png"
        self.mapview.add_widget(marker)
        self.mapview.center_on(self.lat_value, self.lon_value)

        Clock.schedule_once(lambda x: self.start_send(), 0)
        Clock.schedule_once(lambda x: self.add_marks(self.send([self.lat_value, self.lon_value])), 3)
        # auto-sending and displaying data
        Clock.schedule_interval(lambda x: self.add_marks(self.send([self.lat_value, self.lon_value])), self.time)

    # update time of screen update, depending the player is right now (catcher or runner)
    def update_data(self):
        if game_app.role == "runner":
            self.time = 10
        elif game_app.role == "catcher":
            self.time = 5
        self.mapview.center_on(self.lat_value, self.lon_value)
        self.role_label.text = f"You are {game_app.role}"

    # initial connection, it is sending current position and reciving role and player id randomly generated on
    # the server
    def start_send(self):
        msg = "start"
        start_msg = pickle.dumps(msg)
        self.client.send(start_msg)
        ans = self.client.recv(self.HEADER)
        answer = pickle.loads(ans)
        game_app.id = answer[0]
        game_app.role = answer[1]
        cords = [self.lat_value, self.lon_value]
        start_cords = pickle.dumps(cords)
        self.client.send(start_cords)
        self.update_data()

    # it's sending name choosen by player and his cords. Reciving list of dictionaries. First dict is his current data,
    # second dictionary are the players closest to him.
    def send(self, cord: list):
        name = game_app.name
        to_send_dict = {"name": name, "cord": cord}
        msg = "cord"
        cord_msg = pickle.dumps(msg)
        self.client.send(cord_msg)
        msg = pickle.dumps(to_send_dict)
        self.client.send(msg)
        list_to_show = self.client.recv(self.HEADER)
        answer_list = pickle.loads(list_to_show)
        game_app.role = answer_list[0]["role"]
        self.update_data()
        return answer_list[1]

    # Function connected player mark button. It sends catcher and "catched" player id's and reciving True or False.
    # Depending if they are close enough to catch.
    def send_catch(self, player2):
        text = "catch"
        password = pickle.dumps(text)
        self.client.send(password)
        id_list = [game_app.id, player2]
        to_send = pickle.dumps(id_list)
        self.client.send(to_send)
        ans = self.client.recv(4096)
        answer = pickle.loads(ans)
        if answer:
            text = "You catched other player. Now run!"
            game_app.role = "runner"
            self.role_label.text = text
        else:
            text = "You are to far. Try to catch when you will be closer."
            self.role_label.text = text
        Clock.schedule_once(lambda x: self.update_data(), 3)

    # Adds all the marks to the map.
    def add_marks(self, answer):
        for marker in self.all_markers:
            self.mapview.remove_marker(marker)
        for key in answer:
            marker = MapMarkerPopup(lat=answer[key]["cord"][0], lon=answer[key]["cord"][1])
            marker.source = "icons/8GKM2.png"
            if game_app.role == "catcher":
                button1 = Button(text=f"Try to catch {answer[key]['name']}",
                                 size_hint=(2, .5),
                                 on_press=lambda x: self.send_catch(key))
                marker.add_widget(button1)
            else:
                label1 = Label(text=f"Run away from {answer[key]['name']}. It is catcher.", markup=True)
                marker.add_widget(label1)
            self.mapview.add_widget(marker)
            self.all_markers.append(marker)

    # checking current location of the map, and rewrite variables
    def location(self):
        accuracy = 3
        pshellcomm = ['powershell', 'add-type -assemblyname system.device; '
                                    '$loc = new-object system.device.location.geocoordinatewatcher;'
                                    '$loc.start(); '
                                    'while(($loc.status -ne "Ready") -and ($loc.permission -ne "Denied")) '
                                    '{start-sleep -milliseconds 100}; '
                                    '$acc = %d; '
                                    'while($loc.position.location.horizontalaccuracy -gt $acc) '
                                    '{start-sleep -milliseconds 100; $acc = [math]::Round($acc*1.5)}; '
                                    '$loc.position.location.latitude; '
                                    '$loc.position.location.longitude; '
                                    '$loc.position.location.horizontalaccuracy; '
                                    '$loc.stop()' % accuracy]
        p = sp.Popen(pshellcomm, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.STDOUT, text=True)
        (out, err) = p.communicate()
        out = re.split('\n', out)
        lat = float(out[0].replace(",", "."))
        long = float(out[1].replace(",", "."))
        self.lat_value = lat
        self.lon_value = long


class CatchUpApp(App):
    id = None
    status = None
    role = None
    name = None
    lat = GameLayout.lat_value
    lon = GameLayout.lon_value

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_page = GameLayout()
        self.login_page = LoginLayout()
        self.screen_manager = ScreenManager()

    def build(self):
        screen = Screen(name="Login")
        screen.add_widget(self.login_page)
        self.screen_manager.add_widget(screen)

        screen = Screen(name="Game")
        screen.add_widget(self.game_page)
        self.screen_manager.add_widget(screen)

        return self.screen_manager


if __name__ == "__main__":
    game_app = CatchUpApp()
    game_app.run()
