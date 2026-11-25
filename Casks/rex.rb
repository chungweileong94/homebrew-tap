cask "rex" do
  version "0.1.0,2107"
  sha256 "f86fab532e5918dc5502094aa239dacdae62b90661ec0823e43153e14970242f"

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
