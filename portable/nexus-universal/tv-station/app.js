"use strict";
const $ = (id) => document.getElementById(id);
let token = null, busy = false, ready = false;
let history = [];
function bubble(role,text){
  const p=document.createElement("p");
  p.className="bubble "+role;
  p.textContent=text;
  $("messages").appendChild(p);
  $("messages").scrollTop=$("messages").scrollHeight;
}
function controls(){
  $("send").disabled=busy||!ready;
  $("send").textContent=busy?"Yanıt hazırlanıyor…":"Gönder";
}
async function check(){
  $("status").textContent="Kontrol ediliyor…";
  ready=false;controls();
  try{
    const [tr,hr]=await Promise.all([
      fetch("/api/token",{cache:"no-store"}),
      fetch("/api/health",{cache:"no-store"})
    ]);
    if(!tr.ok)throw new Error("Güvenli oturum açılamadı");
    const t=await tr.json(),h=await hr.json();
    if(typeof t.token!=="string")throw new Error("Oturum anahtarı yok");
    token=t.token;
    ready=Boolean(hr.ok&&h.ready===true&&h.local_only===true);
    $("model-status").textContent=ready?"Qwen3 8B kullanıma hazır.":(
      h.reason==="model_missing"?"Model eksik. Bu bilgisayarda: ollama pull qwen3:8b":
      "Ollama erişilemiyor. Bu bilgisayarda Ollama'yı aç."
    );
    $("status").textContent=ready?"● HAZIR":"● KURULUM GEREKLİ";
  }catch(e){
    $("model-status").textContent="Yerel servis bağlantısı hatası: "+e.message;
    $("status").textContent="● BAĞLANTI HATASI";
  }
  controls();
}
$("chat-form").addEventListener("submit",async(e)=>{
  e.preventDefault();
  const prompt=$("prompt").value.trim();
  if(!ready||busy||!prompt||prompt.length>2000)return;
  busy=true;controls();$("prompt").value="";
  bubble("user",prompt);
  try{
    const response=await fetch("/api/chat",{
      method:"POST",
      headers:{"Content-Type":"application/json","X-Nexus-Token":token},
      body:JSON.stringify({prompt,history:history.slice(-8)})
    });
    const obj=await response.json();
    if(!response.ok||typeof obj.answer!=="string"){
      throw new Error(obj.error||"Model cevap veremedi");
    }
    bubble("assistant",obj.answer);
    history.push({role:"user",content:prompt},{role:"assistant",content:obj.answer.slice(0,2000)});
    history=history.slice(-8);
  }catch(e){
    bubble("assistant","İstek tamamlanamadı: "+e.message+". İstasyonu kontrol et.");
  }finally{
    busy=false;controls();$("prompt").focus();
  }
});
$("clear").addEventListener("click",()=>{
  history=[];$("messages").replaceChildren();
  bubble("assistant","Sohbet temizlendi. Yeni bir soru yazabilirsin.");
  $("prompt").focus();
});
$("refresh").addEventListener("click",check);
check();
