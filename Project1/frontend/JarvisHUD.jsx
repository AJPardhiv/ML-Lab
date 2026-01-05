import React, { useEffect, useRef, useState } from 'react'
export default function JarvisHUD(){
  const videoRef=useRef(null); const canvasRef=useRef(null); const wsRef=useRef(null);
  const [connected,setConnected]=useState(false); const [gesture,setGesture]=useState('—'); const [log,setLog]=useState([]);
  useEffect(()=>{ if(navigator.mediaDevices) navigator.mediaDevices.getUserMedia({video:true}).then(s=>{videoRef.current.srcObject=s}); const ws=new WebSocket('ws://localhost:8000/ws'); wsRef.current=ws; ws.onopen=()=>{setConnected(true); push('Connected')}; ws.onmessage=(e)=>{const m=JSON.parse(e.data); if(m.type==='gesture'){setGesture(m.gesture); push(`G:${m.gesture}->${m.action}`)} else if(m.type==='landmarks'){draw(m.landmarks)}}; ws.onclose=()=>setConnected(false); return ()=>{ if(wsRef.current) wsRef.current.close() } },[])
  function push(t){ setLog(prev=>[t,...prev].slice(0,40)) }
  function draw(landmarks){ const c=canvasRef.current, v=videoRef.current; if(!c||!v) return; c.width=v.videoWidth; c.height=v.videoHeight; const ctx=c.getContext('2d'); ctx.clearRect(0,0,c.width,c.height); ctx.fillStyle='rgba(0,255,0,0.9)'; for(let p of landmarks){ctx.beginPath(); ctx.arc(p.x*c.width,p.y*c.height,4,0,Math.PI*2); ctx.fill()} }
  return (<div className="hud"><video ref={videoRef} autoPlay muted playsInline style={{width:'100%'}}/><canvas ref={canvasRef} style={{position:'absolute',left:0,top:0}}/><div>Gesture:{gesture}</div><div><ul>{log.map((l,i)=><li key={i}>{l}</li>)}</ul></div></div>) }
