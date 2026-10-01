/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Sampled from the real NSS emblem (navy ring + red wheel-of-hands), not an
        // invented tech palette — see public/nss-logo.png.
        paper: '#F1EEE3',
        ink: '#201C16',
        navy: { DEFAULT: '#1B2A63', 50: '#EEF0F8', 100: '#DCE1F1', 400: '#3B4E96', 500: '#293E7A', 700: '#152150', 800: '#101A40', 900: '#0F1738' },
        // 'brand' is an alias onto navy so every existing bg-brand-*/text-brand-*/ring-brand-*
        // across the app (there are ~30 files using it) repaints as the new civic navy
        // identity instead of the old purple, without having to touch each file.
        brand: { 50: '#EEF0F8', 100: '#DCE1F1', 200: '#C3CBE8', 300: '#8FA0D2', 400: '#3B4E96', 500: '#293E7A', 600: '#1F2F68', 700: '#1B2A63', 800: '#152150', 900: '#0F1738' },
        flag: { DEFAULT: '#C7291F', 50: '#FBEDEC', 100: '#F5D2CF', 600: '#A81F17' }, // the red wheel — accent, not a wash
        olive: { DEFAULT: '#55643A', 50: '#EEF0E7', 100: '#DAE0CB' }, // ABP1 / environmental
        ochre: { DEFAULT: '#B4791F', 50: '#FBF1DF', 100: '#F3DCA9' }, // certificates, hours, seals
      },
      fontFamily: {
        display: ['"Fraunces"', 'ui-serif', 'Georgia', 'serif'],
        sans: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: { none: '0px', sm: '2px', DEFAULT: '2px', md: '3px', lg: '4px', xl: '4px', '2xl': '6px', full: '9999px' },
      boxShadow: { soft: '0 1px 0 rgba(32,28,22,.08), 0 1px 3px rgba(32,28,22,.05)' },
    },
  },
  plugins: [],
}
