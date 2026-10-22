---
name: lang-csharp
description: C# / .NET apps (console, WinForms, WPF, Avalonia), Unity scripts
domain: csharp
triggers: [c#, csharp, dotnet, .net, winforms, wpf, avalonia, unity]
---
- New: `dotnet new console -o App` (or winforms / wpf / avalonia.app). Build: `dotnet build`; run: `dotnet run`; test: `dotnet test`.
- Errors look like `File.cs(12,5): error CS0103` - fix that line, rebuild.
- WinForms menu: `var ms = new MenuStrip(); var f = new ToolStripMenuItem("&File"); f.DropDownItems.Add("&Open", null, OnOpen); ms.Items.Add(f); MainMenuStrip = ms; Controls.Add(ms);`
- Traps: async void only for event handlers; update UI on the UI thread (Invoke / Dispatcher).
