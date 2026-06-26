/* ============================================================
   Mortal Shell II Guide — Main JavaScript
   Minimal, performance-conscious interactions
   ============================================================ */
(function(){
  'use strict';

  // Mobile nav toggle
  const toggle = document.getElementById('nav-toggle');
  const navList = document.getElementById('nav-list');
  if(toggle && navList){
    toggle.addEventListener('click',function(){
      navList.classList.toggle('open');
      toggle.setAttribute('aria-expanded',navList.classList.contains('open'));
    });
    // Close nav on outside click
    document.addEventListener('click',function(e){
      if(!toggle.contains(e.target) && !navList.contains(e.target)){
        navList.classList.remove('open');
        toggle.setAttribute('aria-expanded','false');
      }
    });
    // Close nav on link click (mobile)
    navList.querySelectorAll('a').forEach(function(a){
      a.addEventListener('click',function(){
        navList.classList.remove('open');
        toggle.setAttribute('aria-expanded','false');
      });
    });
  }

  // Back to top button
  var btt = document.getElementById('back-to-top');
  if(btt){
    var bttThrottle = false;
    window.addEventListener('scroll',function(){
      if(bttThrottle) return;
      bttThrottle = true;
      requestAnimationFrame(function(){
        if(window.scrollY > 600){
          btt.classList.add('visible');
        } else {
          btt.classList.remove('visible');
        }
        bttThrottle = false;
      });
    });
    btt.addEventListener('click',function(){
      window.scrollTo({top:0,behavior:'smooth'});
    });
  }

  // Reading progress bar
  var progBar = document.getElementById('reading-progress');
  if(progBar){
    window.addEventListener('scroll',function(){
      var h = document.documentElement;
      var st = h.scrollTop || document.body.scrollTop;
      var sh = h.scrollHeight - h.clientHeight;
      var pct = sh > 0 ? (st/sh)*100 : 0;
      progBar.style.width = pct + '%';
    });
  }

  // Smooth scroll for anchor links (handled by CSS scroll-behavior:smooth)
  // Additional offset for sticky header
  document.querySelectorAll('a[href^="#"]').forEach(function(a){
    a.addEventListener('click',function(e){
      var target = document.querySelector(this.getAttribute('href'));
      if(target){
        e.preventDefault();
        var top = target.getBoundingClientRect().top + window.pageYOffset - 80;
        window.scrollTo({top:top,behavior:'smooth'});
      }
    });
  });

  // FAQ toggle
  document.querySelectorAll('.faq-item h3').forEach(function(h3){
    h3.addEventListener('click',function(){
      var p = this.nextElementSibling;
      if(p && p.tagName === 'P'){
        var open = p.style.display !== 'none';
        p.style.display = open ? 'none' : '';
        this.setAttribute('aria-expanded',!open);
      }
    });
  });

})();
