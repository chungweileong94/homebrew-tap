cask "rex" do
  version "0.1.0,2130"
  sha256 "81604f103ca023e115c5d322a3624250cce90284627207d5fd287c667c4bb08b"

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
