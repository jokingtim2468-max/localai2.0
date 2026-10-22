---
name: lang-java
description: Java apps and Minecraft mods (Gradle, Maven, Fabric)
domain: java
triggers: [java, gradle, maven, jar, minecraft, fabric, forge, mod, swing, javafx]
---
- Build with the project's wrapper: `./gradlew build` (Windows: `.\gradlew.bat build`); Maven: `mvn package`. Never javac by hand in a Gradle project.
- Fabric mods: `./gradlew runClient` to test; jar in build/libs. Match Java version to the Minecraft version (1.21.x -> Java 21).
- Swing menu: `JMenuBar b = new JMenuBar(); JMenu f = new JMenu("File"); f.add(new JMenuItem("Open")); b.add(f); frame.setJMenuBar(b);`
- Traps: UI work on the EDT (SwingUtilities.invokeLater); read the first "error:" line.
