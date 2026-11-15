cask "kiri" do
  arch arm: "arm64", intel: "x86_64"

  version "0.2.1"

  on_arm do
    sha256 "c42c518eb6a4efcb995b52b987b83e848028a020eef5872e0ac16a1c7827fffa"
  end
  on_intel do
    sha256 "66e5e9f6255ba109e1740078994d8346fbce3c1d7f77075699f3f7f6b9314cff"
  end

  url "https://github.com/libracoder/kiri/releases/download/v#{version}/Kiri-#{version}-#{arch}.dmg"
  name "Kiri"
  desc "Lightweight container runtime compatible with Docker CLI and Compose"
  homepage "https://runkiri.com/"

  livecheck do
    url :url
    strategy :github_latest
  end

  auto_updates true
  depends_on macos: :sonoma

  app "Kiri.app"
end
