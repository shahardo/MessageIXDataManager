# MessageIX Data Manager Icons

This directory contains the application icons for the MessageIX Data Manager.

## Icon Design

The application icon is inspired by the official MessageIX logo and represents the energy systems modeling framework:

- **MESSAGEIX Text**: Clean, modern typography spelling out "MESSAGEIX"
- **Accent Elements**: Subtle geometric shapes representing data and energy systems
- **Background Glow**: Soft circular background for visual appeal
- **Color Scheme**:
  - Blue (#2563EB): Data and technology
  - Dark Blue (#1E40AF): Primary text color
  - Green (#059669): Energy and sustainability
  - Purple (#7C3AED): Accent elements

## Files

- `messageix_data_manager.ico`: Main Windows ICO file with multiple sizes (16x16 to 256x256)
- `icon_{size}x{size}.png`: Individual PNG files for each size
- `excel_icon_{size}x{size}.png`: Excel spreadsheet icons for XLSX files (16x16, 32x32, 48x48, 64x64)
- `generate_icon.py`: Python script to regenerate main application icons programmatically
- `generate_excel_icon.py`: Python script to regenerate Excel icons programmatically

## Usage

The icon is automatically integrated into the PyQt5 application:

- Application icon (taskbar) - uses multi-size PNG approach for best compatibility
- Window icon (title bar)
- File associations (when applicable)

The application loads multiple PNG sizes (256x256, 128x128, 64x64, 48x48, 32x32, 16x16) into a single QIcon for optimal display across different contexts.

## Regenerating Icons

To modify the icon design, edit `generate_icon.py` and run:

```bash
python assets/icons/generate_icon.py
```

This will regenerate all icon sizes and the ICO file. The ICO file is kept for compatibility but PNG files are used for the actual application icons.
