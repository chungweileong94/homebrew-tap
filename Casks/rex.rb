cask "rex" do
  version "0.1.0,1729"
  sha256 "18a99fbb3abb84db9c833b5fd23a9a0abf300914a0068bcfc4c329581f1fe1a1"

  url "https://blob.superlogical.com/public/rex-app/snapshot/Rex-#{version.csv.first}-#{version.csv.second}.dmg"
  name "Rex Beta"
  desc "Terminal emulator and multiplexer (snapshot)"
  homepage "https://www.superlogical.com/rex"

  livecheck do
    url "https://blob.superlogical.com/public/rex-app/snapshot/appcast.xml"
    strategy :sparkle
  end

  auto_updates true
  depends_on macos: :sequoia

  app "Rex Beta.app"

  zap trash: [
    "~/Library/Application Support/com.superlogical.rex",
    "~/Library/Preferences/com.superlogical.rex.plist",
  ]
end
