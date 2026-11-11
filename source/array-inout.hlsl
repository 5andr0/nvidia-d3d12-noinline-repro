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
[noinline] void scaled(inout uint packet[2]) {
 precise uint v=packet[0]*packet[1]; packet[0]=v;
}
[noinline] void dot0x(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void dot0y(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void dot0z(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void weight0(inout float packet[2]) {
 precise float v=packet[0]*packet[1]; packet[0]=v;
}
[noinline] void dot1x(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void dot1y(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void dot1z(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void weight1(inout float packet[2]) {
 precise float v=packet[0]*packet[1]; packet[0]=v;
}
[noinline] void sum1(inout float packet[2]) {
 precise float v=packet[0]+packet[1]; packet[0]=v;
}
[noinline] void dot2x(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void dot2y(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void dot2z(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void weight2(inout float packet[2]) {
 precise float v=packet[0]*packet[1]; packet[0]=v;
}
[noinline] void sum2(inout float packet[2]) {
 precise float v=packet[0]+packet[1]; packet[0]=v;
}
[noinline] void dot3x(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void dot3y(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void dot3z(inout float packet[8]) {
 precise float v=dot(float4(packet[0],packet[1],packet[2],packet[3]),float4(packet[4],packet[5],packet[6],packet[7])); packet[0]=v;
}
[noinline] void weight3(inout float packet[2]) {
 precise float v=packet[0]*packet[1]; packet[0]=v;
}
[noinline] void sum3(inout float packet[2]) {
 precise float v=packet[0]+packet[1]; packet[0]=v;
}
Output main(Input v) {
 Output o;
 uint packet_b0[2]={v.index.x,3u};
 scaled(packet_b0);
 uint b0=packet_b0[0];
 uint packet_b1[2]={v.index.y,3u};
 scaled(packet_b1);
 uint b1=packet_b1[0];
 uint packet_b2[2]={v.index.z,3u};
 scaled(packet_b2);
 uint b2=packet_b2[0];
 uint packet_b3[2]={v.index.w,3u};
 scaled(packet_b3);
 uint b3=packet_b3[0];
 uint i0x=b0+0u;
 float4 r0x=asfloat(i0x<1536u ? rows[min(i0x,1535u)] : uint4(0,0,0,0));
 float packet_d0x[8]={v.p.x,v.p.y,v.p.z,v.p.w,r0x.x,r0x.y,r0x.z,r0x.w};
 dot0x(packet_d0x);
 float d0x=packet_d0x[0];
 uint i0y=b0+1u;
 float4 r0y=asfloat(i0y<1536u ? rows[min(i0y,1535u)] : uint4(0,0,0,0));
 float packet_d0y[8]={v.p.x,v.p.y,v.p.z,v.p.w,r0y.x,r0y.y,r0y.z,r0y.w};
 dot0y(packet_d0y);
 float d0y=packet_d0y[0];
 uint i0z=b0+2u;
 float4 r0z=asfloat(i0z<1536u ? rows[min(i0z,1535u)] : uint4(0,0,0,0));
 float packet_d0z[8]={v.p.x,v.p.y,v.p.z,v.p.w,r0z.x,r0z.y,r0z.z,r0z.w};
 dot0z(packet_d0z);
 float d0z=packet_d0z[0];
 const float4 savedY=r0y; const float4 savedZ=r0z;
 float packet_w0x[2]={d0x,v.w.x};
 weight0(packet_w0x);
 float w0x=packet_w0x[0];
 float packet_w0y[2]={d0y,v.w.x};
 weight0(packet_w0y);
 float w0y=packet_w0y[0];
 float packet_w0z[2]={d0z,v.w.x};
 weight0(packet_w0z);
 float w0z=packet_w0z[0];
 float a0x=w0x;
 float a0y=w0y;
 float a0z=w0z;
 uint i1x=b1+0u;
 float4 r1x=asfloat(i1x<1536u ? rows[min(i1x,1535u)] : uint4(0,0,0,0));
 float packet_d1x[8]={v.p.x,v.p.y,v.p.z,v.p.w,r1x.x,r1x.y,r1x.z,r1x.w};
 dot1x(packet_d1x);
 float d1x=packet_d1x[0];
 uint i1y=b1+1u;
 float4 r1y=asfloat(i1y<1536u ? rows[min(i1y,1535u)] : uint4(0,0,0,0));
 float packet_d1y[8]={v.p.x,v.p.y,v.p.z,v.p.w,r1y.x,r1y.y,r1y.z,r1y.w};
 dot1y(packet_d1y);
 float d1y=packet_d1y[0];
 uint i1z=b1+2u;
 float4 r1z=asfloat(i1z<1536u ? rows[min(i1z,1535u)] : uint4(0,0,0,0));
 float packet_d1z[8]={v.p.x,v.p.y,v.p.z,v.p.w,r1z.x,r1z.y,r1z.z,r1z.w};
 dot1z(packet_d1z);
 float d1z=packet_d1z[0];
 float packet_w1x[2]={d1x,v.w.y};
 weight1(packet_w1x);
 float w1x=packet_w1x[0];
 float packet_w1y[2]={d1y,v.w.y};
 weight1(packet_w1y);
 float w1y=packet_w1y[0];
 float packet_w1z[2]={d1z,v.w.y};
 weight1(packet_w1z);
 float w1z=packet_w1z[0];
 float packet_a1x[2]={a0x,w1x};
 sum1(packet_a1x);
 float a1x=packet_a1x[0];
 float packet_a1y[2]={a0y,w1y};
 sum1(packet_a1y);
 float a1y=packet_a1y[0];
 float packet_a1z[2]={a0z,w1z};
 sum1(packet_a1z);
 float a1z=packet_a1z[0];
 uint i2x=b2+0u;
 float4 r2x=asfloat(i2x<1536u ? rows[min(i2x,1535u)] : uint4(0,0,0,0));
 float packet_d2x[8]={v.p.x,v.p.y,v.p.z,v.p.w,r2x.x,r2x.y,r2x.z,r2x.w};
 dot2x(packet_d2x);
 float d2x=packet_d2x[0];
 uint i2y=b2+1u;
 float4 r2y=asfloat(i2y<1536u ? rows[min(i2y,1535u)] : uint4(0,0,0,0));
 float packet_d2y[8]={v.p.x,v.p.y,v.p.z,v.p.w,r2y.x,r2y.y,r2y.z,r2y.w};
 dot2y(packet_d2y);
 float d2y=packet_d2y[0];
 uint i2z=b2+2u;
 float4 r2z=asfloat(i2z<1536u ? rows[min(i2z,1535u)] : uint4(0,0,0,0));
 float packet_d2z[8]={v.p.x,v.p.y,v.p.z,v.p.w,r2z.x,r2z.y,r2z.z,r2z.w};
 dot2z(packet_d2z);
 float d2z=packet_d2z[0];
 float packet_w2x[2]={d2x,v.w.z};
 weight2(packet_w2x);
 float w2x=packet_w2x[0];
 float packet_w2y[2]={d2y,v.w.z};
 weight2(packet_w2y);
 float w2y=packet_w2y[0];
 float packet_w2z[2]={d2z,v.w.z};
 weight2(packet_w2z);
 float w2z=packet_w2z[0];
 float packet_a2x[2]={a1x,w2x};
 sum2(packet_a2x);
 float a2x=packet_a2x[0];
 float packet_a2y[2]={a1y,w2y};
 sum2(packet_a2y);
 float a2y=packet_a2y[0];
 float packet_a2z[2]={a1z,w2z};
 sum2(packet_a2z);
 float a2z=packet_a2z[0];
 uint i3x=b3+0u;
 float4 r3x=asfloat(i3x<1536u ? rows[min(i3x,1535u)] : uint4(0,0,0,0));
 float packet_d3x[8]={v.p.x,v.p.y,v.p.z,v.p.w,r3x.x,r3x.y,r3x.z,r3x.w};
 dot3x(packet_d3x);
 float d3x=packet_d3x[0];
 uint i3y=b3+1u;
 float4 r3y=asfloat(i3y<1536u ? rows[min(i3y,1535u)] : uint4(0,0,0,0));
 float packet_d3y[8]={v.p.x,v.p.y,v.p.z,v.p.w,r3y.x,r3y.y,r3y.z,r3y.w};
 dot3y(packet_d3y);
 float d3y=packet_d3y[0];
 uint i3z=b3+2u;
 float4 r3z=asfloat(i3z<1536u ? rows[min(i3z,1535u)] : uint4(0,0,0,0));
 float packet_d3z[8]={v.p.x,v.p.y,v.p.z,v.p.w,r3z.x,r3z.y,r3z.z,r3z.w};
 dot3z(packet_d3z);
 float d3z=packet_d3z[0];
 float packet_w3x[2]={d3x,v.w.w};
 weight3(packet_w3x);
 float w3x=packet_w3x[0];
 float packet_w3y[2]={d3y,v.w.w};
 weight3(packet_w3y);
 float w3y=packet_w3y[0];
 float packet_w3z[2]={d3z,v.w.w};
 weight3(packet_w3z);
 float w3z=packet_w3z[0];
 float packet_a3x[2]={a2x,w3x};
 sum3(packet_a3x);
 float a3x=packet_a3x[0];
 float packet_a3y[2]={a2y,w3y};
 sum3(packet_a3y);
 float a3y=packet_a3y[0];
 float packet_a3z[2]={a2z,w3z};
 sum3(packet_a3z);
 float a3z=packet_a3z[0];
 o.blended=float4(a3x,a3y,a3z,1.0);
 o.firstY=savedY; o.firstZ=savedZ; o.fourthY=r3y; o.fourthZ=r3z;
 o.firstRaw=float4(d0x,d0y,d0z,1.0); o.fourthRaw=float4(d3x,d3y,d3z,1.0);
 return o;
}
