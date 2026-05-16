/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./static/js/**/*.js",
        "./static/src/**/*.css",
        "./app.py",
        "./services/**/*.py",
        "./*.py"
    ],
    theme: {
        extend: {
            colors: {
                indigo: {
                    500: '#6366f1',
                    600: '#4f46e5',
                },
            },
            fontFamily: {
                heading: ['Outfit', 'sans-serif'],
                sans: ['Inter', 'sans-serif'],
            },
        },
    },
    safelist: [
        {
            pattern: /(bg|text|border)-(indigo|emerald|amber|red|blue|slate)-(400|500|600)/,
            variants: ['hover', 'focus', 'group-hover'],
        },
        'status-online',
        'status-offline',
    ],
    plugins: [],
}