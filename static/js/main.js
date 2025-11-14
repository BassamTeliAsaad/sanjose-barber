// theme toggle
const themeToggle = document.getElementById('themeToggle');
if(themeToggle){
  const apply = (t)=> document.documentElement.classList.toggle('dark', t==='dark');
  const stored = localStorage.getItem('sjb_theme') || 'light';
  apply(stored);
  themeToggle.addEventListener('click', ()=>{
    const now = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
    localStorage.setItem('sjb_theme', now);
    apply(now);
  });
}
