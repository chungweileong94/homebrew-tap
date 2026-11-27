cask "rex" do
  version "0.1.0,2169"
  sha256 "87319a4de47dbba741e4f4a4419108cdb57abccb57b00ff074fad8838b9059ef"

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
