// Authored diagnostic189. Synthetic inputs only; no recovered game source.
// One hypothesis test; no native chronology or reproduction claim.
cbuffer Palette : register(b1) { uint4 rows[1536]; }
struct Input { float4 p : POS; float4 w : WEIGHT; uint4 index : INDEX; };
struct Output {
 float4 blended : SV_Position;
 float4 firstY : ROW0; float4 firstZ : ROW1;
 float4 fourthY : ROW2; float4 fourthZ : ROW3;
 float4 firstRaw : RAW0; float4 fourthRaw : RAW1;
};
[noinline] uint scaled(uint a, uint b) { precise uint v=a*b; return v; }
[noinline] float dot0x(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float dot0y(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float dot0z(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float weight0(float a,float b) { precise float v=a*b; return v; }
[noinline] float dot1x(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float dot1y(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float dot1z(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float weight1(float a,float b) { precise float v=a*b; return v; }
[noinline] float sum1(float a,float b) { precise float v=a+b; return v; }
[noinline] float dot2x(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float dot2y(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float dot2z(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float weight2(float a,float b) { precise float v=a*b; return v; }
[noinline] float sum2(float a,float b) { precise float v=a+b; return v; }
[noinline] float dot3x(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float dot3y(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float dot3z(float a, float b, float c, float d, float e, float f, float g, float h) {
 precise float v=dot(float4(a,b,c,d),float4(e,f,g,h)); return v;
}
[noinline] float weight3(float a,float b) { precise float v=a*b; return v; }
[noinline] float sum3(float a,float b) { precise float v=a+b; return v; }
Output main(Input v) {
 Output o;
 uint b0=scaled(v.index.x,3u);
 uint b1=scaled(v.index.y,3u);
 uint b2=scaled(v.index.z,3u);
 uint b3=scaled(v.index.w,3u);
 uint i0x=b0+0u;
 float4 r0x=asfloat(i0x<1536u ? rows[min(i0x,1535u)] : uint4(0,0,0,0));
 float d0x=dot0x(v.p.x,v.p.y,v.p.z,v.p.w,r0x.x,r0x.y,r0x.z,r0x.w);
 uint i0y=b0+1u;
 float4 r0y=asfloat(i0y<1536u ? rows[min(i0y,1535u)] : uint4(0,0,0,0));
 float d0y=dot0y(v.p.x,v.p.y,v.p.z,v.p.w,r0y.x,r0y.y,r0y.z,r0y.w);
 uint i0z=b0+2u;
 float4 r0z=asfloat(i0z<1536u ? rows[min(i0z,1535u)] : uint4(0,0,0,0));
 float d0z=dot0z(v.p.x,v.p.y,v.p.z,v.p.w,r0z.x,r0z.y,r0z.z,r0z.w);
 const float4 savedY=r0y; const float4 savedZ=r0z;
 float w0x=weight0(d0x,v.w.x);
 float w0y=weight0(d0y,v.w.x);
 float w0z=weight0(d0z,v.w.x);
 float a0x=w0x;
 float a0y=w0y;
 float a0z=w0z;
 uint i1x=b1+0u;
 float4 r1x=asfloat(i1x<1536u ? rows[min(i1x,1535u)] : uint4(0,0,0,0));
 float d1x=dot1x(v.p.x,v.p.y,v.p.z,v.p.w,r1x.x,r1x.y,r1x.z,r1x.w);
 uint i1y=b1+1u;
 float4 r1y=asfloat(i1y<1536u ? rows[min(i1y,1535u)] : uint4(0,0,0,0));
 float d1y=dot1y(v.p.x,v.p.y,v.p.z,v.p.w,r1y.x,r1y.y,r1y.z,r1y.w);
 uint i1z=b1+2u;
 float4 r1z=asfloat(i1z<1536u ? rows[min(i1z,1535u)] : uint4(0,0,0,0));
 float d1z=dot1z(v.p.x,v.p.y,v.p.z,v.p.w,r1z.x,r1z.y,r1z.z,r1z.w);
 float w1x=weight1(d1x,v.w.y);
 float w1y=weight1(d1y,v.w.y);
 float w1z=weight1(d1z,v.w.y);
 float a1x=sum1(a0x,w1x);
 float a1y=sum1(a0y,w1y);
 float a1z=sum1(a0z,w1z);
 uint i2x=b2+0u;
 float4 r2x=asfloat(i2x<1536u ? rows[min(i2x,1535u)] : uint4(0,0,0,0));
 float d2x=dot2x(v.p.x,v.p.y,v.p.z,v.p.w,r2x.x,r2x.y,r2x.z,r2x.w);
 uint i2y=b2+1u;
 float4 r2y=asfloat(i2y<1536u ? rows[min(i2y,1535u)] : uint4(0,0,0,0));
 float d2y=dot2y(v.p.x,v.p.y,v.p.z,v.p.w,r2y.x,r2y.y,r2y.z,r2y.w);
 uint i2z=b2+2u;
 float4 r2z=asfloat(i2z<1536u ? rows[min(i2z,1535u)] : uint4(0,0,0,0));
 float d2z=dot2z(v.p.x,v.p.y,v.p.z,v.p.w,r2z.x,r2z.y,r2z.z,r2z.w);
 float w2x=weight2(d2x,v.w.z);
 float w2y=weight2(d2y,v.w.z);
 float w2z=weight2(d2z,v.w.z);
 float a2x=sum2(a1x,w2x);
 float a2y=sum2(a1y,w2y);
 float a2z=sum2(a1z,w2z);
 uint i3x=b3+0u;
 float4 r3x=asfloat(i3x<1536u ? rows[min(i3x,1535u)] : uint4(0,0,0,0));
 float d3x=dot3x(v.p.x,v.p.y,v.p.z,v.p.w,r3x.x,r3x.y,r3x.z,r3x.w);
 uint i3y=b3+1u;
 float4 r3y=asfloat(i3y<1536u ? rows[min(i3y,1535u)] : uint4(0,0,0,0));
 float d3y=dot3y(v.p.x,v.p.y,v.p.z,v.p.w,r3y.x,r3y.y,r3y.z,r3y.w);
 uint i3z=b3+2u;
 float4 r3z=asfloat(i3z<1536u ? rows[min(i3z,1535u)] : uint4(0,0,0,0));
 float d3z=dot3z(v.p.x,v.p.y,v.p.z,v.p.w,r3z.x,r3z.y,r3z.z,r3z.w);
 float w3x=weight3(d3x,v.w.w);
 float w3y=weight3(d3y,v.w.w);
 float w3z=weight3(d3z,v.w.w);
 float a3x=sum3(a2x,w3x);
 float a3y=sum3(a2y,w3y);
 float a3z=sum3(a2z,w3z);
 o.blended=float4(a3x,a3y,a3z,1.0);
 o.firstY=savedY; o.firstZ=savedZ; o.fourthY=r3y; o.fourthZ=r3z;
 o.firstRaw=float4(d0x,d0y,d0z,1.0); o.fourthRaw=float4(d3x,d3y,d3z,1.0);
 return o;
}
