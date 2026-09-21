import concurrent.futures
import os
import socket
import subprocess
import threading
from kivy.app import App
from kivy.clock import mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView


def speak(text):
  os.system(f'termux-tts-speak "{text}" >/dev/null 2>&1')


def get_wifi_base_ip():
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('10.255.255.255', 1))
    ip = s.getsockname()[0]
    s.close()
    return '.'.join(ip.split('.')[:3])
  except Exception:
    return '192.168.1'


def ping_ip(ip):
  try:
    res = subprocess.run(
        ['ping', '-c', '1', '-W', '1', ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return ip if res.returncode == 0 else None
  except Exception:
    return None


def resolve_device_name(ip):
  try:
    hostname = socket.gethostbyaddr(ip)[0]
    if hostname and hostname != ip:
      return hostname.split('.')[0]
  except Exception:
    pass
  return 'Appareil inconnu'


class PocketSOCApp(App):

  def build(self):
    self.title = 'PocketSOC'

    layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

    self.label_status = Label(
        text='PocketSOC OS', size_hint_y=0.15, font_size='20sp', bold=True
    )
    layout.add_widget(self.label_status)

    self.scroll = ScrollView(size_hint=(1, 0.7))
    self.results_label = Label(
        text='Appuyez sur le bouton pour scanner.',
        size_hint_y=None,
        font_size='15sp',
        halign='left',
        valign='top',
    )
    self.results_label.bind(
        texture_size=lambda instance, value: setattr(instance, 'height', value[1])
    )
    self.results_label.bind(
        size=lambda instance, value: setattr(instance, 'text_size', (value[0], None))
    )
    self.scroll.add_widget(self.results_label)
    layout.add_widget(self.scroll)

    btn_scan = Button(
        text='Lancer Scan Réseau',
        size_hint_y=0.15,
        background_color=(0, 0.8, 0.4, 1),
        font_size='16sp',
    )
    btn_scan.bind(on_press=self.start_scan)
    layout.add_widget(btn_scan)

    return layout

  def start_scan(self, instance):
    self.label_status.text = 'Scan en cours...'
    self.results_label.text = 'Analyse du réseau Wi-Fi...\n'
    speak('Analyse du réseau démarrée.')
    threading.Thread(target=self.run_network_scan, daemon=True).start()

  def run_network_scan(self):
    base_ip = get_wifi_base_ip()
    ip_list = [f'{base_ip}.{i}' for i in range(1, 255)]
    active_ips = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
      results_ping = executor.map(ping_ip, ip_list)
      for ip in results_ping:
        if ip:
          active_ips.append(ip)

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
      names = list(executor.map(resolve_device_name, active_ips))

    output_lines = []
    speech_phrases = []

    for ip, dev_name in zip(active_ips, names):
      output_lines.append(f'IP: {ip:<15} | Nom: {dev_name}')
      spoken_ip = ip.replace('.', ' point ')
      speech_phrases.append(f'Adresse {spoken_ip}, nom : {dev_name}')

    if not output_lines:
      out_text = 'Aucun appareil trouvé.'
      speech_text = 'Aucun appareil trouvé. Fin des appareils trouvés.'
    else:
      out_text = '\n'.join(output_lines)
      speech_text = (
          f'Scan terminé. {len(active_ips)} appareils trouvés : '
          + '. '.join(speech_phrases)
          + '. Fin des appareils trouvés.'
      )

    self.update_ui(out_text, speech_text)

  @mainthread
  def update_ui(self, out_text, speech_text):
    self.label_status.text = 'Scan terminé'
    self.results_label.text = out_text
    speak(speech_text)


if __name__ == '__main__':
  PocketSOCApp().run()
      
