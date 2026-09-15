from tools.patch_quake3_ios import (
    patch_app_delegate,
    patch_game_view_controller,
    patch_storyboard,
    patch_sys_main,
)


def test_game_view_controller_launches_hijacked_as_direct_non_bot_map():
    source = '''
class GameViewController: UIViewController {
    var selectedMap = ""
    var botMatch = false
    var bots = [(name: String, skill: Float, icon: String)]()
    let defaults = UserDefaults()
    func launch() {
        let documentsDir = "/tmp/Documents"
        Sys_SetHomeDir(documentsDir)
        var argv: [String?] = [ Bundle.main.resourcePath! + "/quake3", "+set", "com_basegame", "baseq3", "+name", self.defaults.string(forKey: "playerName")]

        if !self.selectedMap.isEmpty {
            if self.botMatch {
                argv.append("+map")
            } else {
                argv.append("+spmap")
            }
            argv.append(self.selectedMap)

            if !self.botMatch {
                argv.append("+g_spSkill")
                argv.append(String(self.selectedDifficulty))
            }
        }

        if self.botMatch {
            for bot in self.bots {
                argv.append("+addbot")
                argv.append(bot.name)
            }
        }
    }
}
'''
    patched = patch_game_view_controller(source)
    assert 'var selectedMap = "hijacked"' in patched
    assert 'var botMatch = false' in patched
    assert 'var botMatch = true' not in patched
    assert 'self.defaults.string(forKey: "playerName") ?? "HijackedPlayer"' in patched
    assert '"+set", "fs_basepath", Bundle.main.resourcePath!' in patched
    assert '"+set", "fs_apppath", Bundle.main.resourcePath!' in patched
    assert '"+set", "fs_homepath", documentsDir' in patched
    assert '"+set", "logfile", "2"' in patched
    assert 'argv.append("+spmap")' not in patched
    assert 'argv.append("+g_spSkill")' not in patched
    assert 'argv.append("+map")' in patched
    assert 'argv.append("+addbot")' in patched


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


def test_sys_main_traces_engine_startup_and_first_frame_boundaries():
    source = '''
#ifdef IOS
void Sys_Startup( int argc, char **argv )
#else
int main( int argc, char **argv )
#endif // IOS
{
    int i;
    char commandLine[ MAX_STRING_CHARS ] = { 0 };
    SDL_version ver;
    SDL_GetVersion( &ver );
    Sys_PlatformInit( );
    Sys_Milliseconds( );
    Sys_ParseArgs( argc, argv );
    Sys_SetBinaryPath( Sys_Dirname( argv[ 0 ] ) );
    Sys_SetDefaultInstallPath( DEFAULT_BASEDIR );
    CON_Init( );
    Com_Init( commandLine );
    NET_Init( );
    while( 1 )
    {
        Com_Frame( );
    }
}
'''
    patched = patch_sys_main(source)
    assert 'static void HijackedEngineTrace' in patched
    assert 'HijackedEngineTrace("Sys_Startup:entered")' in patched
    assert 'HijackedEngineTrace("Sys_Startup:afterPlatformInit")' in patched
    assert 'HijackedEngineTrace("Sys_Startup:beforeComInit")' in patched
    assert 'HijackedEngineTrace("Sys_Startup:afterComInit")' in patched
    assert 'HijackedEngineTrace("Sys_Startup:afterNetInit")' in patched
    assert 'HijackedEngineTrace("Sys_Startup:firstFrame:before")' in patched
    assert 'HijackedEngineTrace("Sys_Startup:firstFrame:after")' in patched
