import os
from pathlib import Path
import xml.etree.ElementTree as ET


def write_xml(tree, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tree.write(tmp, encoding='utf-8', xml_declaration=True)
    tmp.chmod(0o600)
    tmp.replace(path)


def configure(game, profile):
    # Preserve unknown settings, mod selections and other GIANTS-managed nodes.
    path = game / 'dedicatedServer.xml'
    tree = ET.parse(path) if path.exists() else ET.ElementTree(ET.Element('server'))
    root = tree.getroot()
    def node(parent, name):
        found = parent.find(name)
        return found if found is not None else ET.SubElement(parent, name)
    web = node(root, 'webserver')
    web.set('port', os.environ.get('WEB_PORT', '7999'))
    admin = node(web, 'initial_admin')
    node(admin, 'username').text = os.environ.get('WEB_USERNAME', 'admin')
    node(admin, 'passphrase').text = os.environ['WEB_PASSWORD']
    node(web, 'tls').set('active', 'false')
    game_node = node(root, 'game')
    game_node.attrib.update(description='Farming Simulator 25', name='FarmingSimulator2025', exe='FarmingSimulator2025Game.exe')
    write_xml(tree, path)

    path = profile / 'dedicated_server' / 'dedicatedServerConfig.xml'
    tree = ET.parse(path) if path.exists() else ET.ElementTree(ET.Element('gameserver'))
    settings = node(tree.getroot(), 'settings')
    values = {
        'game_name': os.environ.get('SERVER_NAME', 'FS25 Server'),
        'admin_password': os.environ['SERVER_ADMIN'],
        'game_password': os.environ.get('SERVER_PASSWORD', ''),
        'port': os.environ['SERVER_PORT'],
        'max_player': os.environ.get('SERVER_PLAYERS', '16'),
        'language': os.environ.get('SERVER_REGION', 'en'),
        'auto_save_interval': os.environ.get('SERVER_SAVE_INTERVAL', '3'),
        'stats_interval': os.environ.get('SERVER_STATS_INTERVAL', '360'),
        'crossplay_allowed': os.environ.get('SERVER_CROSSPLAY', 'true'),
        'pause_game_if_empty': os.environ.get('SERVER_PAUSE', '2'),
        'savegame_index': os.environ.get('SAVEGAME_INDEX', '1'),
    }
    for key, value in values.items():
        node(settings, key).text = value
    # Map and economy are initial settings; preserve an existing world's choices.
    for key, value in {'mapID': os.environ.get('SERVER_MAP', 'MapUS'), 'mapFilename': 'default',
                       'initialMoney': '500000', 'initialLoan': '0', 'economicDifficulty': '2'}.items():
        if settings.find(key) is None:
            node(settings, key).text = value
    write_xml(tree, path)
