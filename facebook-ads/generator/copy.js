// Per-screenshot ad copy. box = feature area as fractions of the screenshot.
// h[0..6] = headline for designs 1..7 (h[4] supports *gold* emphasis).
module.exports = [
  {
    file: 'IMG_5723.jpg', slug: '01_ai-tutor', eyebrow: 'New · AI Tutor',
    items: [
      { t: 'Your AI tutor, 24/7', d: 'Ask any NPTE question. Get it explained in plain words.', box: { x0: .037, x1: .963, y0: .298, y1: .531 } },
      { t: 'Mistakes come back', d: 'Missed questions return until you’ve nailed them.', box: { x0: .037, x1: .963, y0: .544, y1: .641 } },
    ],
    h: ['Study smarter for the NPTE.', 'Meet the tutor that never clocks out.', 'Ask anything. Forget nothing.',
      'Your NPTE coach, in your pocket.', 'Stuck at 2 AM? *Just ask.*', 'Two features that change how you study', 'Your NPTE, explained.'],
    stat: ['24/7', 'AI tutor for every NPTE question'],
  },
  {
    file: 'IMG_5724.jpg', slug: '02_full-exams', eyebrow: 'Full NPTE-PT exams',
    items: [
      { t: '5 full NPTE-PT exams', d: '225 questions each, 5 timed sections, just like test day.', box: { x0: .037, x1: .963, y0: .323, y1: .418 } },
      { t: 'See where you stand', d: 'Weekly scores, best system and weakest area at a glance.', box: { x0: .037, x1: .963, y0: .642, y1: .835 } },
    ],
    h: ['Rehearse test day before test day.', 'Train like it’s the real NPTE.', 'No surprises on exam day.',
      'Practice the full exam.', 'Know your weak spot *before the NPTE does.*', 'Full exams + live performance tracking', 'Test day? Ready.'],
    stat: ['225', 'questions per full-length exam'],
  },
  {
    file: 'IMG_5725.jpg', slug: '03_progress', eyebrow: 'Progress & analytics',
    items: [
      { t: 'Performance analytics', d: 'Pacing, question types and your weakest topics.', box: { x0: .037, x1: .963, y0: .268, y1: .335 } },
      { t: 'Review every attempt', d: 'Go back through any quiz, question by question.', box: { x0: .037, x1: .963, y0: .354, y1: .523 } },
    ],
    h: ['Your progress, finally measured.', 'Stop guessing what to study next.', 'Every quiz tells you something.',
      'Turn every attempt into progress.', 'Find your gaps. *Close them fast.*', 'See exactly where your points are hiding', 'Measure. Fix. Pass.'],
    stat: ['1 tap', 'to review any past attempt'],
  },
  {
    file: 'IMG_5726.jpg', slug: '04_built-to-pass', eyebrow: 'About our content',
    items: [
      { t: '2,600 NPTE questions', d: 'Plus 5 full exams and 700+ flashcards across 14 areas.', box: { x0: .067, x1: .933, y0: .454, y1: .55 } },
      { t: 'Written by PT educators', d: 'Exam-style scenarios with teacher-style rationales.', box: { x0: .037, x1: .963, y0: .65, y1: .962 } },
    ],
    h: ['Built to pass the NPTE.', '2,600 questions. One goal: your license.', 'Written by PT educators. Not bots.',
      'Built to pass the NPTE.', 'Every answer explained, *not just marked.*', 'Serious NPTE prep, right in your pocket', 'Built to pass.'],
    stat: ['2,600', 'exam-style NPTE questions'],
  },
  {
    file: 'IMG_5727.jpg', slug: '05_blueprint', eyebrow: 'Matched to the blueprint',
    items: [
      { t: 'Weighted like the real exam', d: 'Questions per area match the official FSBPT outline.', box: { x0: .037, x1: .963, y0: .108, y1: .62 } },
      { t: 'Built on trusted textbooks', d: 'O’Sullivan, Magee, Kisner, Umphred, Goodman & more.', box: { x0: .037, x1: .76, y0: .7, y1: .962 } },
    ],
    h: ['Practice exactly what the NPTE tests.', 'Every question weighted like test day.', 'No filler. Just the real blueprint.',
      'Study what actually shows up.', 'Backed by the books *your professors trust.*', 'The right topics, in the right amounts', 'Blueprint-matched.'],
    stat: ['62', 'Musculoskeletal questions per full exam'],
  },
  {
    file: 'IMG_5721.jpg', slug: '06_app-overview', eyebrow: 'Your all-in-one NPTE prep',
    items: [
      { t: 'A daily goal, made for you', d: 'Smart Retests target the system that needs you most today.', box: { x0: .037, x1: .963, y0: .142, y1: .325 } },
      { t: 'Quiz any system', d: 'Musculoskeletal, Neuro, Cardio, Peds & more, from 2,600 questions.', box: { x0: .037, x1: .963, y0: .409, y1: .812 } },
    ],
    h: ['Pass NPTE with Confidence'],
  },
  {
    file: 'IMG_5722.jpg', slug: '07_build-your-quiz', eyebrow: 'Your all-in-one NPTE prep',
    items: [
      { t: 'Study or Exam mode', d: 'Rationales as you go, or timed with no hints.', box: { x0: .037, x1: .963, y0: .206, y1: .455 } },
      { t: 'Build your own quiz', d: 'Pick how many questions from each system, up to 225.', box: { x0: .037, x1: .963, y0: .469, y1: .842 } },
    ],
    h: ['Your Quiz. Your Way.<br>Your Pass.'],
  },
];
