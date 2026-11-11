// Authored synthetic fixtures. CPU only; no graphics API or recovered data.
#include "common.h"
#include <filesystem>
#include <fstream>
#include <iostream>
template<class T> void append(Bytes& b,T v){auto p=reinterpret_cast<const unsigned char*>(&v);b.insert(b.end(),p,p+sizeof(v));}
void write(const std::filesystem::path& p,const Bytes& b){std::ofstream f(p,std::ios::binary|std::ios::trunc);need(bool(f),"create fixture");f.write(reinterpret_cast<const char*>(b.data()),static_cast<std::streamsize>(b.size()));need(bool(f),"write fixture");}
int main(){try{
 std::filesystem::create_directories("data");
 constexpr float position[4][4]={{1,2,3,1},{2,1,4,1},{3,2,1,1},{1,3,2,1}};
 constexpr uint32_t indices[4][4]={{1,2,3,4},{4,3,2,1},{7,5,9,2},{2,7,1,9}};
 Bytes vb,cb,bad;
 for(size_t v=0;v<4;++v){for(float x:position[v])append(vb,x);for(unsigned j=1;j<=4;++j)append(vb,static_cast<float>(j));for(uint32_t i:indices[v])append(vb,i);}
 for(unsigned i=1;i<=6144;++i)append(cb,static_cast<float>(i));
 constexpr uint32_t historical[]={0x4528c000u,0x456ec000u,0x45802000u,0x3f800000u,0x42540000u,0x42580000u,0x425c0000u,0x42600000u,0x42640000u,0x42680000u,0x426c0000u,0x42700000u,0x42540000u,0x42580000u,0x425c0000u,0x42600000u,0x42640000u,0x42680000u,0x426c0000u,0x42700000u,0x42cc0000u,0x43bf0000u,0x43cd0000u,0x3f800000u,0x43b10000u,0x43bf0000u,0x43cd0000u,0x3f800000u,0x45048000u,0x44b90000u,0x44e10000u,0x3f800000u,0x41880000u,0x41900000u,0x41980000u,0x41a00000u,0x41a80000u,0x41b00000u,0x41b80000u,0x41c00000u,0x41880000u,0x41900000u,0x41980000u,0x41a00000u,0x41a80000u,0x41b00000u,0x41b80000u,0x41c00000u,0x43ca0000u,0x43140000u,0x43340000u,0x3f800000u,0x42e80000u,0x43140000u,0x43340000u,0x3f800000u,0x458ce000u,0x45034000u,0x4514c000u,0x3f800000u,0x41e80000u,0x41f00000u,0x41f80000u,0x42000000u,0x42040000u,0x42080000u,0x420c0000u,0x42100000u,0x41e80000u,0x41f00000u,0x41f80000u,0x42000000u,0x42040000u,0x42080000u,0x420c0000u,0x42100000u,0x44168000u,0x43520000u,0x436e0000u,0x3f800000u,0x43360000u,0x43520000u,0x436e0000u,0x3f800000u,0x4595b000u,0x45fa5000u,0x46018800u,0x3f800000u,0x42e20000u,0x42e40000u,0x42e60000u,0x42e80000u,0x42ea0000u,0x42ec0000u,0x42ee0000u,0x42f00000u,0x42e20000u,0x42e40000u,0x42e60000u,0x42e80000u,0x42ea0000u,0x42ec0000u,0x42ee0000u,0x42f00000u,0x43390000u,0x44484000u,0x444f4000u,0x3f800000u,0x44414000u,0x44484000u,0x444f4000u,0x3f800000u};
 static_assert(sizeof(historical)==448);
 for(uint32_t bits:historical)append(bad,bits);
 auto expected=oracle(vb,cb);
 write("data/synthetic-VB.bin",vb);write("data/synthetic-CB.bin",cb);write("data/oracle.bin",expected);write("data/known-bad.bin",bad);
 std::cout<<"Generated exact synthetic inputs, oracle and historical comparison fixture. No graphics executed.\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
