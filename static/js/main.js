// theme toggle (dark/light) persisted in localStorage
const btn = document.getElementById('themeToggle');
if(btn){
  const setTheme = (dark)=>{
    document.body.classList.toggle('theme-dark', dark);
    localStorage.setItem('sjb_theme_dark', dark ? '1' : '0');
  };
  const pref = localStorage.getItem('sjb_theme_dark');
  setTheme(pref === '1');
  btn.addEventListener('click', ()=> setTheme(!document.body.classList.contains('theme-dark')) );
}
