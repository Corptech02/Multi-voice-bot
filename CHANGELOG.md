# Changelog

All notable changes to the Multi-Tab Claude Voice Bot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.0] - 2025-08-11

### Added
- Comprehensive mobile responsive design for smartphones
- iPhone-specific optimizations (tested on iPhone 12)
- Responsive width adjustments for all UI elements

### Changed
- Chat log repositioned and resized for mobile screens
- Control buttons optimized for touch interfaces
- Text input and send button properly sized for mobile
- All text elements centered on mobile devices

### Fixed
- Right-side cutoff issues on mobile screens
- Chat log no longer overlaps control buttons
- Message text wrapping to prevent horizontal overflow
- Proper spacing between all UI elements on small screens

## [2.3.1] - 2025-08-11

### Fixed
- Bot responses now work correctly after page refresh with saved sessions
- Sessions are created on-demand when first message is sent after restore
- Improved session restoration logic to avoid conflicts

## [2.3.0] - 2025-08-11

### Added
- Save state toggle (💾) to persist sessions across devices
- Auto-save functionality when bot responds
- Server-side session storage in JSON file
- Session restore on page load when save is enabled
- TTS endpoint for voice announcements

### Changed
- Sessions now persist across browser refreshes when save is enabled
- Chat history and tab names are preserved when switching devices

## [2.2.0] - 2025-08-11

### Added
- Settings button with configuration panel
- Multiple chime sound options (Default, Bell, Ding, Soft)
- Voice announcement mode - speaks tab name instead of chime
- Settings persistence in localStorage
- Test sound button in settings

### Changed
- Notification system now supports both chime and voice modes
- Chime function accepts tab ID for voice announcements

## [2.1.0] - 2025-08-11

### Added
- Per-request stats display (timer and tokens reset after each response)
- Terminal monitor integration for debugging
- Processing indicator (⏳) during active Claude requests
- Token formatting with k-notation (1.0k, 2.5k, etc.)

### Changed
- Stats now work like Claude AI - showing only current request metrics
- Timer only counts during Claude processing time
- Improved stats box UI with grid layout matching exact specifications

### Fixed
- Duplicate thread creation issue in send_command
- Thread synchronization problems causing stats to stop
- Stats were showing cumulative totals instead of per-request

## [2.0.0] - 2025-08-10

### Added
- Multi-tab support (up to 4 simultaneous Claude sessions)
- Real-time voice interaction with edge-tts
- WebSocket-based real-time updates
- Session state management per tab
- Visual indicators for active/unread tabs
- HTTPS support with self-signed certificates

### Changed
- Complete rewrite from single-session to multi-tab architecture
- Migrated from HTTP polling to WebSocket communication
- Enhanced UI with exact replica of Claude.ai design

## [1.0.0] - 2025-08-09

### Added
- Initial release with single session support
- Basic voice input/output functionality
- Simple web interface
- Claude API integration