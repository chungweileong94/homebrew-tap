# Homebrew tap

Personal Homebrew casks maintained by [chungweileong94](https://github.com/chungweileong94).

## Install Rex

```sh
brew install --cask chungweileong94/tap/rex
```

This automatically taps this repository and installs **Rex Beta.app**. The current preview requires **macOS 15 (Sequoia) or later** and supports both Apple Silicon and Intel Macs.

This is an unofficial tap, not affiliated with Superlogical. Rex is preview software; see the vendor's [installation and testing information](https://www.superlogical.com/rex/docs/installation).

## Updates

Rex has a built-in updater. It checks at launch and daily, and downloads an update when you choose to install it. See [Superlogical's update documentation](https://www.superlogical.com/rex/docs/reference/privacy).

To upgrade with Homebrew after the version in this tap has been updated:

```sh
brew update
brew upgrade --cask --greedy chungweileong94/tap/rex
```

`--greedy` includes casks marked `auto_updates`. It does not discover or install a version newer than the one declared in this tap.

Maintainers can check the upstream preview feed with:

```sh
brew livecheck --cask chungweileong94/tap/rex
```

Livecheck only detects new versions; it does not automatically edit or publish the cask. No scheduled updater is configured. Update both the version/build and SHA-256 when a new preview is published.

## Download integrity

The supplied `latest.dmg` endpoint changes as previews are released. This cask instead uses the equivalent versioned download from Rex's own Sparkle feed, with a fixed SHA-256 checksum. The DMG is downloaded directly from Superlogical; this repository does not redistribute it.

Initial cask: version **0.1.0**, build **1408**. Its versioned DMG was verified byte-for-byte identical to the vendor's `latest.dmg` on 25 October 2026. The bundle name, minimum macOS version, update feed and universal executable architecture were inspected directly from that DMG without running Rex.

## Remove

```sh
brew uninstall --cask chungweileong94/tap/rex
```

This cask deliberately has no `zap` rules, so it does not remove Rex settings or session data.

## Maintainer checks

On a Mac with Homebrew:

```sh
brew style --cask chungweileong94/tap/rex
brew audit --cask --online chungweileong94/tap/rex
brew livecheck --cask chungweileong94/tap/rex
```
