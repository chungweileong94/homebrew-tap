cask "rex" do
  version "0.1.0,2146"
  sha256 "9159742dcbc61879ea6a140718e5deeb15564c8eaf67a4ee7ac7cd66d4261925"

  url "https://blob.superlogical.com/public/rex-app/snapshot/Rex-#{version.csv.first}-#{version.csv.second}.dmg"
  name "Rex"
  desc "Terminal emulator and multiplexer (snapshot)"
  homepage "https://www.superlogical.com/rex"

  livecheck do
    url "https://blob.superlogical.com/public/rex-app/snapshot/appcast.xml"
    strategy :sparkle
  end

  auto_updates true
  depends_on macos: :sequoia

  app "Rex.app"

  zap trash: [
    "~/Library/Application Support/com.superlogical.rex",
    "~/Library/Preferences/com.superlogical.rex.plist",
  ]
end
