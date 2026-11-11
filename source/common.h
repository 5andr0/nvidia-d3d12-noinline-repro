// Authored portable diagnostic250 CPU logic. No graphics headers or calls.
#pragma once
#include <vector>
#include <string>
#include <stdexcept>
#include <cstdint>
#include <cstring>
#include <algorithm>
using Bytes=std::vector<unsigned char>;
inline void need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
inline uint32_t word(const Bytes& b,size_t at){need(at<=b.size()&&b.size()-at>=4,"word bounds");uint32_t v;memcpy(&v,b.data()+at,4);return v;}
inline uint64_t u64(const Bytes& b,size_t at){need(at<=b.size()&&b.size()-at>=8,"u64 bounds");uint64_t v;memcpy(&v,b.data()+at,8);return v;}
inline bool finite(const Bytes& b){if(b.size()%4)return false;for(size_t i=0;i<b.size();i+=4)if((word(b,i)&0x7f800000)==0x7f800000)return false;return true;}
inline uint32_t integer(uint32_t b){auto e=(b>>23)&255;need(!(b>>31)&&e>=127&&e<=150,"positive integral binary32");auto d=1u<<(150-e),m=(b&0x7fffff)|0x800000;need(m%d==0,"integral mantissa");return m/d;}
inline void encode(Bytes& b,uint32_t v){need(v>0&&v<(1u<<24),"exact integer range");unsigned e=0;for(auto n=v;n>1;n>>=1)++e;auto bits=((e+127)<<23)|((v-(1u<<e))<<(23-e));for(unsigned j=0;j<4;++j)b.push_back(static_cast<unsigned char>(bits>>(8*j)));}
inline Bytes oracle(const Bytes& vb,const Bytes& cb){
 need(vb.size()==192&&cb.size()==24576,"input shape");
 for(size_t i=0;i<6144;++i)need(integer(word(cb,i*4))==i+1,"literal palette");
 Bytes out;uint32_t maximum=0;
 for(size_t v=0;v<4;++v){uint32_t p[4],w[4],ix[4],rows[12][4],dot[12]={},blend[3]={};
  for(size_t j=0;j<4;++j){p[j]=integer(word(vb,v*48+j*4));need(p[j]<=16,"position bound");w[j]=integer(word(vb,v*48+16+j*4));need(w[j]==j+1,"weight pattern");ix[j]=word(vb,v*48+32+j*4);need(ix[j]>=1&&ix[j]<=9,"index bounds");for(size_t k=0;k<j;++k)need(ix[k]!=ix[j],"distinct indices");}
  for(size_t r=0;r<12;++r)for(size_t j=0;j<4;++j){rows[r][j]=integer(word(cb,(ix[r/3]*3+r%3)*16+j*4));auto product=rows[r][j]*p[j];dot[r]+=product;maximum=(std::max)(maximum,(std::max)(product,dot[r]));}
  for(size_t a=0;a<3;++a)for(size_t k=0;k<4;++k){auto product=dot[k*3+a]*w[k];blend[a]+=product;maximum=(std::max)(maximum,(std::max)(product,blend[a]));}
  for(auto x:blend)encode(out,x);encode(out,1);
  for(auto r:{1,2,10,11})for(auto x:rows[r])encode(out,x);
  for(auto r:{0,9}){for(size_t j=0;j<3;++j)encode(out,dot[r+j]);encode(out,1);}
 }
 need(maximum==5350&&out.size()==448,"independent exact oracle maximum/shape");return out;
}
struct Layout {size_t stride,payload,counter,query,total,count;};
constexpr Layout candidateLayout{112,448,576,584,600,4};
static_assert(candidateLayout.payload==candidateLayout.stride*candidateLayout.count);
static_assert(candidateLayout.counter%8==0&&candidateLayout.query%8==0);
inline bool accounting(const Bytes& b){return b.size()==600&&std::all_of(b.begin(),b.begin()+64,[](auto x){return x==0xa5;})&&std::all_of(b.begin()+512,b.begin()+576,[](auto x){return x==0xa5;})&&u64(b,576)==448&&u64(b,584)==4&&u64(b,592)==4;}
inline std::string classify(const Bytes& output,const Bytes& good,const Bytes& bad,bool clean){if(!clean||output.size()!=448||good.size()!=448||bad.size()!=448||!finite(output))return "INCOMPLETE/ERROR";return output==good?"CORRECT":output==bad?"KNOWN_BAD":"OTHER_FINITE_MISMATCH";}
enum class Mode {List,Vendor,Luid,Warp};
struct Options {Mode mode=Mode::List;uint32_t vendor=0,low=0,high=0;std::wstring output;};
inline uint32_t hex32(const std::wstring& s){need(!s.empty()&&s.size()<=8,"LUID requires 1..8 hex digits per half");uint32_t v=0;for(auto c:s){unsigned d=c>=L'0'&&c<=L'9'?c-L'0':c>=L'a'&&c<=L'f'?c-L'a'+10:c>=L'A'&&c<=L'F'?c-L'A'+10:99;need(d<16,"LUID hex digits");v=v*16+d;}return v;}
inline Options parse(const std::vector<std::wstring>& args){Options o;bool selected=false,output=false;for(size_t i=0;i<args.size();++i){auto a=args[i];if(a==L"--output"){need(!output&&i+1<args.size(),"one output value required");o.output=args[++i];need(!o.output.empty(),"nonempty output");output=true;continue;}need(!selected,"exactly one selector");selected=true;if(a==L"--list")o.mode=Mode::List;else if(a==L"--warp")o.mode=Mode::Warp;else if(a==L"--vendor"){need(i+1<args.size(),"vendor required");auto v=args[++i];need(v==L"nvidia"||v==L"amd","vendor must be nvidia or amd");o.mode=Mode::Vendor;o.vendor=v==L"nvidia"?0x10de:0x1002;}else if(a==L"--luid"){need(i+1<args.size(),"LUID required HIGH:LOW hex");auto v=args[++i];auto k=v.find(L':');need(k!=std::wstring::npos,"LUID HIGH:LOW hex");o.high=hex32(v.substr(0,k));o.low=hex32(v.substr(k+1));o.mode=Mode::Luid;}else need(false,"unknown argument");}need(selected,"explicit selector required");need((o.mode==Mode::List)?!output:output,"list forbids output; run requires fresh output");return o;}
struct AdapterKey {uint32_t vendor,low,high;bool software;};
inline size_t select(const Options& o,const std::vector<AdapterKey>& keys){need(o.mode==Mode::Vendor||o.mode==Mode::Luid,"hardware selector");size_t found=0,count=0;for(size_t i=0;i<keys.size();++i){auto k=keys[i];if(!k.software&&((o.mode==Mode::Vendor&&o.vendor==k.vendor)||(o.mode==Mode::Luid&&o.low==k.low&&o.high==k.high))){found=i;++count;}}need(count!=0,"MISSING_ADAPTER");need(count==1,"AMBIGUOUS_ADAPTER: use --luid");return found;}
