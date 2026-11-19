# iOS accessibility review checklist

**Status:** manual verification required; this checklist is not a completed device test report.

## VoiceOver

- [ ] Launch the library with VoiceOver enabled. Confirm the screen title is announced once and decorative waveform icons are skipped.
- [ ] Move to the import action. Confirm its label and hint explain that the user chooses an audio file they exported.
- [ ] Start an import and confirm the progress label/value is understandable without relying on animation.
- [ ] Trigger a malformed-file import and confirm the status is announced as an error, not only shown in red.
- [ ] Confirm each recording is announced with its import date, duration and size.
- [ ] Confirm share and play/pause actions announce which recording they affect.
- [ ] Adjust playback position and verify the slider announces its current time and total duration.
- [ ] Verify elapsed time, total duration, pause/resume state and end-of-playback are understandable.
- [ ] Change retention and confirm the setting is discoverable and the retention description is readable.
- [ ] Delete a recording and confirm the resulting library state is understandable.

## Dynamic Type and layout

- [ ] Test the largest accessibility text sizes; no critical control or status text is clipped.
- [ ] Test portrait and landscape orientations on supported iPhone sizes.
- [ ] Confirm the recording list remains scrollable when the keyboard or share sheet is presented.
- [ ] Confirm button hit targets remain usable and adjacent share/play controls are distinguishable.
- [ ] Confirm the status message does not rely on color alone to distinguish errors.

## Other input modes

- [ ] Verify Switch Control can reach import, retention, share, playback, seek and delete actions.
- [ ] Verify Voice Control labels can distinguish multiple recordings with different dates.
- [ ] Verify Reduce Motion does not hide progress or state changes.

## Report

Record exact device model, iOS version/build, accessibility settings, test date, failures and screenshots only after removing recording content and personal data. Do not mark this checklist complete based on Simulator build success alone.
