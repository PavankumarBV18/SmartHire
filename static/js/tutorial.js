/* static/js/tutorial.js */

document.addEventListener('DOMContentLoaded', () => {
    const HAS_SEEN_TUTORIAL = localStorage.getItem('smarthire_tutorial_completed');
    const isHomePage = ['/dashboard', '/admin-dashboard'].includes(window.location.pathname);

    // Show tutorial modal automatically if first time and on a home-like page
    if (!HAS_SEEN_TUTORIAL && isHomePage) {
        setTimeout(showWelcomeModal, 800);
    }
});

function showWelcomeModal() {
    const modal = document.getElementById('tutorial-welcome-modal');
    if (modal) {
        modal.classList.add('active');
    }
}

function hideWelcomeModal() {
    const modal = document.getElementById('tutorial-welcome-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function skipTutorial() {
    hideWelcomeModal();
    localStorage.setItem('smarthire_tutorial_completed', 'true');
}

function startTutorial() {
    hideWelcomeModal();
    
    // Check if we are on a valid home page. If not, redirect and set force flag.
    const validPages = ['/', '/index', '/dashboard', '/admin-dashboard'];
    if (!validPages.includes(window.location.pathname)) {
        localStorage.setItem('smarthire_force_tutorial', 'true');
        window.location.href = '/dashboard'; // Default to dashboard for logged-in tour
        return;
    }

    // Configure Intro.js
    const intro = introJs();
    intro.setOptions({
        steps: [
            {
                element: '#upload-card-step',
                title: 'Step 1: Resume Upload',
                intro: 'Upload your resume in PDF format. SmartHire extracts resume content and performs ATS-based analysis instantly.',
                position: 'right'
            },
            {
                element: '#upload-card-step',
                title: 'Step 2: ATS Analyzer',
                intro: 'SmartHire calculates ATS compatibility score and identifies formatting issues, keyword optimization, and recruiter-readiness.',
                position: 'left'
            },
            {
                element: '#nav-jd-analyzer',
                title: 'Step 3: JD Analyzer',
                intro: 'Paste any Job Description to compare your resume with recruiter requirements and identify missing keywords.',
                position: 'bottom'
            },
            {
                element: '#nav-skill-engine',
                title: 'Step 4: Skill Gap Engine',
                intro: 'Discover missing technical and soft skills required for your dream role.',
                position: 'bottom'
            },
            {
                element: '#nav-enhancer',
                title: 'Step 5: Resume Enhancer',
                intro: 'Improve weak resume sections using AI-generated professional suggestions.',
                position: 'bottom'
            },
            {
                element: '#nav-market-trends',
                title: 'Step 6: Market Trends',
                intro: 'Explore trending technologies, tools, certifications, and in-demand industry skills.',
                position: 'bottom'
            },
            {
                element: '#nav-roadmap',
                title: 'Step 7: Career Roadmap Generator',
                intro: 'Generate a personalized learning roadmap to become job-ready step-by-step.',
                position: 'bottom'
            },
            {
                element: '#nav-interview-prep',
                title: 'Step 8: Interview Preparation',
                intro: 'Practice AI-generated interview questions with role-specific preparation guidance.',
                position: 'bottom'
            },
            {
                element: '#nav-compare',
                title: 'Step 9: Resume Comparison',
                intro: 'Compare multiple resumes and identify strengths, weaknesses, and ATS performance differences.',
                position: 'bottom'
            },
            {
                element: '#chat-icon',
                title: 'Step 10: Voice Assistant',
                intro: 'Navigate SmartHire using voice commands for accessibility and hands-free interaction.',
                position: 'top'
            },
            {
                element: '#nav-home', 
                title: 'Step 11: Dashboard Insights',
                intro: 'Track your career improvement progress using SmartHire analytics and recommendations.',
                position: 'bottom'
            }
        ],
        showProgress: true,
        showBullets: false,
        disableInteraction: true,
        scrollToElement: true,
        overlayOpacity: 0.85,
        exitOnOverlayClick: false,
        exitOnEsc: false
    });

    // Voice Narration Setup
    const synth = window.speechSynthesis;
    let currentUtterance = null;

    intro.onchange(function(targetElement) {
        if (synth && synth.speaking) {
            synth.cancel();
        }
        const currentStep = this._introItems[this._currentStep];
        
        // Voice Narration
        if (currentStep && currentStep.intro) {
            const textToSpeak = `${currentStep.title}. ${currentStep.intro}`;
            currentUtterance = new SpeechSynthesisUtterance(textToSpeak);
            currentUtterance.lang = 'en-US';
            currentUtterance.rate = 1.05;
            currentUtterance.pitch = 1;
            synth.speak(currentUtterance);
        }
    });

    intro.onexit(function() {
        if (synth && synth.speaking) synth.cancel();
        localStorage.setItem('smarthire_tutorial_completed', 'true');
    });

    intro.oncomplete(function() {
        if (synth && synth.speaking) synth.cancel();
        localStorage.setItem('smarthire_tutorial_completed', 'true');
        showCompletionModal();
    });

    intro.start();
}

function showCompletionModal() {
    const modal = document.getElementById('tutorial-completion-modal');
    if (modal) {
        modal.classList.add('active');
        triggerConfetti();
    }
}

function hideCompletionModal() {
    const modal = document.getElementById('tutorial-completion-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function triggerConfetti() {
    if (typeof confetti === 'function') {
        const duration = 3000;
        const end = Date.now() + duration;

        (function frame() {
            confetti({
                particleCount: 5,
                angle: 60,
                spread: 55,
                origin: { x: 0 },
                colors: ['#00ffcc', '#3b82f6', '#a855f7']
            });
            confetti({
                particleCount: 5,
                angle: 120,
                spread: 55,
                origin: { x: 1 },
                colors: ['#00ffcc', '#3b82f6', '#a855f7']
            });

            if (Date.now() < end) {
                requestAnimationFrame(frame);
            }
        }());
    }
}

function replayTutorial() {
    hideCompletionModal();
    // Navigate to home page if not there
    if (window.location.pathname !== '/' && window.location.pathname !== '/index') {
        localStorage.setItem('smarthire_force_tutorial', 'true');
        window.location.href = '/';
    } else {
        startTutorial();
    }
}

// Check for force tutorial flag across pages
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('smarthire_force_tutorial') === 'true') {
        localStorage.removeItem('smarthire_force_tutorial');
        setTimeout(startTutorial, 500);
    }
});
