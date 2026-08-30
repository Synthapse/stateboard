---
name: Slate Tactical
colors:
  surface: '#051424'
  surface-dim: '#051424'
  surface-bright: '#2c3a4c'
  surface-container-lowest: '#010f1f'
  surface-container-low: '#0d1c2d'
  surface-container: '#122131'
  surface-container-high: '#1c2b3c'
  surface-container-highest: '#273647'
  on-surface: '#d4e4fa'
  on-surface-variant: '#c5c6cd'
  inverse-surface: '#d4e4fa'
  inverse-on-surface: '#233143'
  outline: '#8f9097'
  outline-variant: '#45474c'
  surface-tint: '#bcc7de'
  primary: '#bcc7de'
  on-primary: '#263143'
  primary-container: '#1e293b'
  on-primary-container: '#8590a6'
  inverse-primary: '#545f73'
  secondary: '#ffb690'
  on-secondary: '#552100'
  secondary-container: '#ec6a06'
  on-secondary-container: '#4a1c00'
  tertiary: '#4cd7f6'
  on-tertiary: '#003640'
  tertiary-container: '#002d36'
  on-tertiary-container: '#009db7'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e3fb'
  primary-fixed-dim: '#bcc7de'
  on-primary-fixed: '#111c2d'
  on-primary-fixed-variant: '#3c475a'
  secondary-fixed: '#ffdbca'
  secondary-fixed-dim: '#ffb690'
  on-secondary-fixed: '#341100'
  on-secondary-fixed-variant: '#783200'
  tertiary-fixed: '#acedff'
  tertiary-fixed-dim: '#4cd7f6'
  on-tertiary-fixed: '#001f26'
  on-tertiary-fixed-variant: '#004e5c'
  background: '#051424'
  on-background: '#d4e4fa'
  surface-variant: '#273647'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-base:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-point:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 24px
  margin: 32px
---

## Brand & Style
The design system embodies a "From Stone to Ascension" philosophy, moving from the heavy, grounded reliability of slate minerals to the light, ethereal clarity of strategic insight. It is designed for high-stakes decision-making environments where cognitive load must be minimized.

The aesthetic is **Slate Tactical**: a refined blend of high-end corporate professionalism and minimalist briefing tools. It utilizes a sophisticated dark-mode foundation to reduce eye strain during extended analytical sessions. The emotional response is one of calm authority, precision, and mission-readiness. Visual complexity is stripped away in favor of purposeful data hierarchy and sharp, intentional accents.

## Colors
The palette is rooted in a spectrum of deep slates and cool grays, providing a low-contrast environment that allows accent colors to vibrate with significance.

- **Primary (Slate):** Used for the architectural foundation, backgrounds, and deep structural elements.
- **Secondary (Orange):** Reserved exclusively for critical decision states, alerts, and high-priority "Action Required" metrics.
- **Tertiary (Cyan):** Applied to navigation, active states, and interactive elements to provide a clear cognitive path through the dashboard.
- **Neutral:** A range of desaturated grays used for secondary text and borders to maintain the "Stone" aesthetic without competing with data.

## Typography
The system uses **Inter** for its neutral, systematic utility across all interface elements, ensuring maximum legibility. To lean into the "briefing" aesthetic, **JetBrains Mono** is introduced for technical labels and data points, providing a precise, monospaced rhythm that suggests data integrity.

- **Headlines:** Use tight tracking and semi-bold weights to create a sense of urgency and command.
- **Data Labels:** Always in uppercase JetBrains Mono to distinguish metadata from content.
- **Body:** Standardized on a 16px base for comfort, utilizing Slate 300 for secondary information to maintain hierarchy.

## Layout & Spacing
This design system utilizes a **12-column fluid grid** for the main dashboard area, allowing modules to scale based on the density of the data. 

- **The Briefing Sidebar:** A fixed-width (280px) navigation area that remains anchored to the left.
- **Spacing Rhythm:** Based on a 4px baseline grid. Padding within data cards should remain generous (24px) to ensure "Ascension" (clarity/breathability) within the "Stone" (dense data).
- **Mobile Reflow:** On mobile devices, the 12-column grid collapses into a single-column stack. Sidebar navigation transforms into a bottom-anchored bar or a full-screen overlay to maintain thumb-reachability.

## Elevation & Depth
In line with the professional briefing aesthetic, elevation is achieved through **Tonal Layers** rather than traditional shadows. 

- **Level 0 (Base):** The darkest slate (#0F172A), used for the application background.
- **Level 1 (Surface):** The primary slate (#1E293B), used for cards and modules.
- **Level 2 (Interaction):** Subtle, low-contrast outlines (1px solid #334155) define boundaries. 
- **Active State:** Cyan glows are used sparingly. When an element is focused, a subtle 4px outer blur of the Tertiary color (#06B6D4) at 20% opacity may be used to signify "Ascension" or active selection.

## Shapes
Shapes are disciplined and architectural. The **Soft (0.25rem)** roundedness level is chosen to take the edge off the "Stone" without losing the professional, tactical feel. 

- **Primary Elements:** 4px radius for buttons, input fields, and small modules.
- **Containers:** 8px (rounded-lg) for main dashboard cards to create a clear container-to-background distinction.
- **Data Indicators:** Status dots and small badges remain sharp or use a minimal 2px radius to appear precise and engineered.

## Components
- **Buttons:** Primary buttons use the Tertiary Cyan background with dark text. Critical action buttons use the Secondary Orange. Ghost buttons use a subtle Slate 700 border.
- **Cards:** Defined by Level 1 surfaces with a 1px border. Header areas within cards should be separated by a subtle horizontal rule.
- **Input Fields:** Darker than the card surface to create a "recessed" look. Focus state is indicated by a 1px Cyan border.
- **Chips/Badges:** Use a desaturated version of the status color (e.g., Alert Orange at 15% opacity) with high-contrast text for status indicators.
- **KPI Modules:** Large JetBrains Mono typography for the primary metric, with a small trend indicator (Cyan for up, Orange for down) positioned to the right of the value.
- **Lists:** Clean, borderless rows with subtle hover states (Slate 800) to maintain a streamlined briefing flow.