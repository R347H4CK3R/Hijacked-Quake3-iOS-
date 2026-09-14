from tools.patch_quake3_ios import patch_app_delegate, patch_game_view_controller, patch_storyboard


def test_game_view_controller_defaults_to_hijacked_and_safe_name():
    source = '''
class GameViewController: UIViewController {
    var selectedMap = ""
    var botMatch = false
    let defaults = UserDefaults()
    func launch() {
        var argv: [String?] = [ Bundle.main.resourcePath! + "/quake3", "+set", "com_basegame", "baseq3", "+name", self.defaults.string(forKey: "playerName")]
    }
}
'''
    patched = patch_game_view_controller(source)
    assert 'var selectedMap = "hijacked"' in patched
    assert 'var botMatch = true' in patched
    assert 'self.defaults.string(forKey: "playerName") ?? "HijackedPlayer"' in patched


def test_storyboard_assigns_hijacked_game_identifier():
    source = '<viewController id="BYZ-38-t0r" customClass="GameViewController" customModule="Quake3_iOS" customModuleProvider="target" sceneMemberID="viewController">'
    patched = patch_storyboard(source)
    assert 'storyboardIdentifier="HijackedGameVC"' in patched
    assert patched.count('storyboardIdentifier="HijackedGameVC"') == 1


def test_app_delegate_launches_hijacked_game_controller_directly():
    source = '''
    UIStoryboard *mainStoryboard = [UIStoryboard storyboardWithName:@"Main" bundle: nil];

    rootNavigationController = (UINavigationController *)[mainStoryboard instantiateViewControllerWithIdentifier:@"RootNC"];

    self.uiwindow.rootViewController = self.rootNavigationController;
'''
    patched = patch_app_delegate(source)
    assert 'instantiateViewControllerWithIdentifier:@"HijackedGameVC"' in patched
    assert 'self.uiwindow.rootViewController = hijackedGameController;' in patched
    assert 'instantiateViewControllerWithIdentifier:@"RootNC"' not in patched
