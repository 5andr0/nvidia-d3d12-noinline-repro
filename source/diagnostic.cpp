// Authored diagnostic250; narrowly derived from authored probe225 / harness189.
// One unchanged scalar-return baseline. CPU preparation is not GPU qualification.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <bcrypt.h>
#include <wrl/client.h>
#include <filesystem>
#include <fstream>
#include <vector>
#include <map>
#include <string>
#include <stdexcept>
#include <iostream>
#include <thread>
#include <chrono>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include "pins.h"
#include "common.h"
#include <d3d12sdklayers.h>
#include <sstream>
#include <iomanip>
#include <tlhelp32.h>
using Microsoft::WRL::ComPtr;
namespace fs=std::filesystem;
void hr(HRESULT h,const char* s){need(SUCCEEDED(h),std::string(s)+" HRESULT="+std::to_string(static_cast<unsigned long>(h)));}
void put(const fs::path& path,const Bytes& b){
 HANDLE h=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);
 need(h!=INVALID_HANDLE_VALUE,"exclusive output create"); DWORD written=0;
 BOOL ok=WriteFile(h,b.data(),static_cast<DWORD>(b.size()),&written,nullptr); BOOL flushed=FlushFileBuffers(h); CloseHandle(h);
 need(ok&&written==b.size()&&flushed,"durable output write");
}
void note(const fs::path& path,const std::string& s){put(path,Bytes(s.begin(),s.end()));}
Bytes read(const fs::path& p){auto n=fs::file_size(p);need(n<1024*1024,"bounded input size");Bytes b(static_cast<size_t>(n));std::ifstream f(p,std::ios::binary);f.read(reinterpret_cast<char*>(b.data()),b.size());need(bool(f),"input read");return b;}
std::string hash(const Bytes& b){
 unsigned char digest[32]; auto status=BCryptHash(BCRYPT_SHA256_ALG_HANDLE,nullptr,0,const_cast<PUCHAR>(b.data()),static_cast<ULONG>(b.size()),digest,32);
 need(status>=0,"SHA256");std::string s;const char* hex="0123456789abcdef";for(auto v:digest){s+=hex[v>>4];s+=hex[v&15];}return s;
}
struct Pending {bool live=false;~Pending(){if(live){TerminateProcess(GetCurrentProcess(),125);std::abort();}}};
struct Context {
 ComPtr<IDXGIFactory4> factory;ComPtr<IDXGIAdapter1> adapter;ComPtr<ID3D12Device> device;
 ComPtr<ID3D12CommandQueue> queue;ComPtr<ID3D12CommandAllocator> allocator;ComPtr<ID3D12GraphicsCommandList> list;
 ComPtr<ID3D12Fence> fence;ComPtr<ID3D12QueryHeap> queries;
 uint64_t serial=0,allocated=0;std::string allocations;fs::path evidence;size_t allocationRequests=0;
 ComPtr<ID3D12Resource> buffer(size_t size,D3D12_HEAP_TYPE type,D3D12_RESOURCE_STATES state,const char* name){
  D3D12_HEAP_PROPERTIES hp={};hp.Type=type;hp.CreationNodeMask=hp.VisibleNodeMask=1;
  D3D12_RESOURCE_DESC d={};d.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;d.Width=size;d.Height=1;d.DepthOrArraySize=1;d.MipLevels=1;d.SampleDesc.Count=1;d.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
  auto a=device->GetResourceAllocationInfo(0,1,&d);
  note(evidence/("ALLOCATION-request-"+std::to_string(allocationRequests++)+".txt"),std::string(name)+"\nrequested="+std::to_string(size)+"\nallocation="+std::to_string(a.SizeInBytes)+"\nprevious_total="+std::to_string(allocated)+"\n");need(a.SizeInBytes!=UINT64_MAX&&a.SizeInBytes<=128ull*1024*1024-allocated,"128MiB explicit allocation cap");
  allocated+=a.SizeInBytes;ComPtr<ID3D12Resource> r;hr(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&d,state,nullptr,IID_PPV_ARGS(&r)),"buffer");
  allocations+=std::string(name)+"\t"+std::to_string(size)+"\t"+std::to_string(a.SizeInBytes)+"\t"+std::to_string(type)+"\t"+std::to_string(r->GetGPUVirtualAddress())+"\n";return r;
 }
 void transition(ID3D12Resource* r,D3D12_RESOURCE_STATES before,D3D12_RESOURCE_STATES after){D3D12_RESOURCE_BARRIER b={};b.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;b.Transition={r,D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,before,after};list->ResourceBarrier(1,&b);}
 void submit(){
  hr(list->Close(),"close command list");ID3D12CommandList* p=list.Get();Pending pending;pending.live=true;
  queue->ExecuteCommandLists(1,&p);hr(queue->Signal(fence.Get(),++serial),"signal");auto start=std::chrono::steady_clock::now();
  for(;;){auto v=fence->GetCompletedValue();need(v!=UINT64_MAX,"device removed while pending");if(v>=serial)break;need(std::chrono::steady_clock::now()-start<std::chrono::seconds(10),"10s fence deadline");Sleep(1);}
  pending.live=false;
 }
 void reset(){hr(allocator->Reset(),"allocator reset after completed fence");hr(list->Reset(allocator.Get(),nullptr),"list reset");}
};
void upload(ID3D12Resource* r,const Bytes& b){void* p=nullptr;D3D12_RANGE range={0,0};hr(r->Map(0,&range,&p),"upload map");need(p!=nullptr,"upload pointer");memcpy(p,b.data(),b.size());D3D12_RANGE written={0,b.size()};r->Unmap(0,&written);}
Bytes download(ID3D12Resource* r,size_t n){void* p=nullptr;D3D12_RANGE range={0,n};hr(r->Map(0,&range,&p),"readback map");need(p!=nullptr,"readback pointer");Bytes b(static_cast<unsigned char*>(p),static_cast<unsigned char*>(p)+n);D3D12_RANGE written={0,0};r->Unmap(0,&written);return b;}
struct Stage {ComPtr<ID3D12RootSignature> root;ComPtr<ID3D12PipelineState> pso;ComPtr<ID3D12Resource> output,readback;std::string name;Layout layout=candidateLayout;};
Stage stage(Context& c,const Bytes& shader,const std::string& name,const fs::path& out){
 Stage s;s.name=name;UINT regs[3]={0,1,2};D3D12_ROOT_PARAMETER params[3]={};
 for(int i=0;i<3;i++){params[i].ParameterType=D3D12_ROOT_PARAMETER_TYPE_CBV;params[i].Descriptor={regs[i],0};params[i].ShaderVisibility=D3D12_SHADER_VISIBILITY_VERTEX;}
 D3D12_ROOT_SIGNATURE_DESC rd={};rd.NumParameters=3;rd.pParameters=params;rd.Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT|D3D12_ROOT_SIGNATURE_FLAG_ALLOW_STREAM_OUTPUT;
 ComPtr<ID3DBlob> rootBytes,errors;HRESULT h=D3D12SerializeRootSignature(&rd,D3D_ROOT_SIGNATURE_VERSION_1,&rootBytes,&errors);
 if(errors){auto p=static_cast<unsigned char*>(errors->GetBufferPointer());put(out/(name+".root-errors.bin"),Bytes(p,p+errors->GetBufferSize()));}hr(h,"serialize root");
 auto rp=static_cast<unsigned char*>(rootBytes->GetBufferPointer());put(out/(name+".root.bin"),Bytes(rp,rp+rootBytes->GetBufferSize()));
 hr(c.device->CreateRootSignature(0,rp,rootBytes->GetBufferSize(),IID_PPV_ARGS(&s.root)),"root signature");
 D3D12_INPUT_ELEMENT_DESC syntheticInputs[3]={{"POS",0,DXGI_FORMAT_R32G32B32A32_FLOAT,0,0,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},{"WEIGHT",0,DXGI_FORMAT_R32G32B32A32_FLOAT,0,16,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},{"INDEX",0,DXGI_FORMAT_R32G32B32A32_UINT,0,32,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0}};
 D3D12_SO_DECLARATION_ENTRY so[7]={{0,"SV_Position",0,0,4,0}};
 for(UINT i=0;i<4;i++)so[i+1]={0,"ROW",i,0,4,0};for(UINT i=0;i<2;i++)so[i+5]={0,"RAW",i,0,4,0};
 UINT stride=static_cast<UINT>(s.layout.stride);
 D3D12_GRAPHICS_PIPELINE_STATE_DESC d={};d.pRootSignature=s.root.Get();d.VS={shader.data(),shader.size()};d.InputLayout={syntheticInputs,3u};d.StreamOutput={so,7u,&stride,1,D3D12_SO_NO_RASTERIZED_STREAM};d.SampleMask=UINT_MAX;d.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_POINT;d.SampleDesc.Count=1;
 d.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;d.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;d.RasterizerState.DepthClipEnable=TRUE;
 d.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_ALWAYS;d.DepthStencilState.FrontFace=d.DepthStencilState.BackFace={D3D12_STENCIL_OP_KEEP,D3D12_STENCIL_OP_KEEP,D3D12_STENCIL_OP_KEEP,D3D12_COMPARISON_FUNC_ALWAYS};
 for(auto& t:d.BlendState.RenderTarget){t.SrcBlend=t.SrcBlendAlpha=D3D12_BLEND_ONE;t.DestBlend=t.DestBlendAlpha=D3D12_BLEND_ZERO;t.BlendOp=t.BlendOpAlpha=D3D12_BLEND_OP_ADD;t.LogicOp=D3D12_LOGIC_OP_NOOP;t.RenderTargetWriteMask=15;}
 hr(c.device->CreateGraphicsPipelineState(&d,IID_PPV_ARGS(&s.pso)),"SO pipeline");
 s.output=c.buffer(s.layout.total,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_COPY_DEST,name.c_str());s.readback=c.buffer(s.layout.total,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST,name.c_str());return s;
}
void draw(Context& c,Stage& s,ID3D12Resource* seed,const std::vector<ComPtr<ID3D12Resource>>& inputs,UINT query){
 auto l=c.list.Get();const auto& x=s.layout;l->CopyBufferRegion(s.output.Get(),0,seed,0,x.total);c.transition(s.output.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_STREAM_OUT);
 l->SetPipelineState(s.pso.Get());l->SetGraphicsRootSignature(s.root.Get());l->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_POINTLIST);
 D3D12_VERTEX_BUFFER_VIEW vb={inputs[0]->GetGPUVirtualAddress(),192u,48u};l->IASetVertexBuffers(0,1,&vb);
 for(UINT j=0;j<3;j++){auto a=inputs[1]->GetGPUVirtualAddress();need(a%256==0,"CBV alignment");l->SetGraphicsRootConstantBufferView(j,a);}
 D3D12_STREAM_OUTPUT_BUFFER_VIEW so={s.output->GetGPUVirtualAddress()+64,x.payload,s.output->GetGPUVirtualAddress()+x.counter};l->SOSetTargets(0,1,&so);
 l->BeginQuery(c.queries.Get(),D3D12_QUERY_TYPE_SO_STATISTICS_STREAM0,query);l->DrawInstanced(static_cast<UINT>(x.count),1,0,0);l->EndQuery(c.queries.Get(),D3D12_QUERY_TYPE_SO_STATISTICS_STREAM0,query);l->SOSetTargets(0,0,nullptr);
 c.transition(s.output.Get(),D3D12_RESOURCE_STATE_STREAM_OUT,D3D12_RESOURCE_STATE_COPY_SOURCE);l->CopyBufferRegion(s.readback.Get(),0,s.output.Get(),0,x.total);l->ResolveQueryData(c.queries.Get(),D3D12_QUERY_TYPE_SO_STATISTICS_STREAM0,query,1,s.readback.Get(),x.query);
}
struct Capture {Bytes payload,pair;bool accounting=false,finitePair=false;};
Capture capture(Stage& s,const fs::path& out){
 const auto& x=s.layout;Bytes b=download(s.readback.Get(),x.total);put(out/(s.name+".audit.bin"),b);
 Capture r;r.payload=Bytes(b.begin()+64,b.begin()+64+x.payload);put(out/(s.name+".outputs.bin"),r.payload);
 for(size_t i=0;i<x.count;i++)r.pair.insert(r.pair.end(),r.payload.begin()+i*x.stride,r.payload.begin()+i*x.stride+32);
 for(size_t half=0;half<2;half++){Bytes v;for(size_t i=0;i<x.count;i++)v.insert(v.end(),r.pair.begin()+i*32+half*16,r.pair.begin()+i*32+half*16+16);put(out/(s.name+(half?".second.bin":".position.bin")),v);}
 bool guards=std::all_of(b.begin(),b.begin()+64,[](auto v){return v==0xa5;})&&std::all_of(b.begin()+64+x.payload,b.begin()+x.counter,[](auto v){return v==0xa5;});
 r.accounting=guards&&accounting(b);r.finitePair=finite(r.pair);
 note(out/(s.name+".accounting.txt"),"filled="+std::to_string(u64(b,x.counter))+"\nwritten="+std::to_string(u64(b,x.query))+"\nneeded="+std::to_string(u64(b,x.query+8))+"\nsentinels="+std::to_string(guards)+"\nfinite_original_pair="+std::to_string(r.finitePair)+"\nsha256="+hash(r.payload)+"\n");return r;
}

std::string utf8(const std::wstring& s){if(s.empty())return {};int n=WideCharToMultiByte(CP_UTF8,0,s.data(),static_cast<int>(s.size()),nullptr,0,nullptr,nullptr);need(n>0,"UTF8 size");std::string r(static_cast<size_t>(n),'\0');need(WideCharToMultiByte(CP_UTF8,0,s.data(),static_cast<int>(s.size()),r.data(),n,nullptr,nullptr)==n,"UTF8 conversion");return r;}
std::string jsonQuote(const std::string& s){std::string r="\"";const char* hex="0123456789abcdef";for(unsigned char c:s){if(c=='"'||c=='\\'){r+='\\';r+=c;}else if(c<32){r+="\\u00";r+=hex[c>>4];r+=hex[c&15];}else r+=c;}return r+'"';}
std::string adapterText(const DXGI_ADAPTER_DESC1& d){std::ostringstream s;s<<"name="<<utf8(d.Description)<<"\nvendor="<<d.VendorId<<"\ndevice="<<d.DeviceId<<"\nsubsystem="<<d.SubSysId<<"\nrevision="<<d.Revision<<"\nsoftware="<<((d.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)!=0)<<"\nluid="<<std::hex<<std::setfill('0')<<std::setw(8)<<static_cast<uint32_t>(d.AdapterLuid.HighPart)<<":"<<std::setw(8)<<d.AdapterLuid.LowPart<<"\n";return s.str();}
fs::path executableDir(){wchar_t p[32768];auto n=GetModuleFileNameW(nullptr,p,32768);need(n>0&&n<32768,"executable path");return fs::path(p).parent_path();}
ComPtr<IDXGIAdapter1> choose(IDXGIFactory4* f,const Options& o){ComPtr<IDXGIAdapter1> result;if(o.mode==Mode::Warp){hr(f->EnumWarpAdapter(IID_PPV_ARGS(&result)),"explicit WARP");DXGI_ADAPTER_DESC1 d={};hr(result->GetDesc1(&d),"WARP description");need((d.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)!=0,"explicit software adapter required");return result;}
 std::vector<ComPtr<IDXGIAdapter1>> adapters;std::vector<AdapterKey> keys;
 for(UINT i=0;i<128;++i){ComPtr<IDXGIAdapter1> a;auto h=f->EnumAdapters1(i,&a);if(h==DXGI_ERROR_NOT_FOUND){if(o.mode==Mode::List)return {};return adapters.at(select(o,keys));}hr(h,"enumerate adapter");DXGI_ADAPTER_DESC1 d={};hr(a->GetDesc1(&d),"adapter description");if(o.mode==Mode::List)std::cout<<adapterText(d)<<"\n";keys.push_back({d.VendorId,d.AdapterLuid.LowPart,static_cast<uint32_t>(d.AdapterLuid.HighPart),(d.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)!=0});adapters.push_back(a);}need(false,"adapter enumeration cap");return {};
}
void words(const fs::path& out,const Bytes& payload,const Bytes& expected){
 need(payload.size()==448&&expected.size()==448,"word report shape");std::ostringstream csv,json;csv<<"word,vertex,field,lane,expected_u32,observed_u32,expected_float,observed_float,equal\n";json<<"[\n";const char* fields[]={"SV_Position","ROW0","ROW1","ROW2","ROW3","RAW0","RAW1"};
 for(size_t i=0;i<112;++i){auto a=word(expected,i*4),b=word(payload,i*4);float x,y;memcpy(&x,&a,4);memcpy(&y,&b,4);csv<<i<<','<<i/28<<','<<fields[(i%28)/4]<<','<<i%4<<','<<a<<','<<b<<','<<std::setprecision(9)<<x<<','<<y<<','<<(a==b)<<'\n';json<<(i?",\n":"")<<"{\"word\":"<<i<<",\"expected_u32\":"<<a<<",\"observed_u32\":"<<b<<",\"equal\":"<<(a==b?"true":"false")<<"}";}
 json<<"\n]\n";note(out/"words.csv",csv.str());note(out/"words.json",json.str());
}
void modules(const fs::path& out){
 HANDLE h=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE,GetCurrentProcessId());need(h!=INVALID_HANDLE_VALUE,"module snapshot");MODULEENTRY32W m={};m.dwSize=sizeof(m);std::string s="module\tbytes\tsha256\n";BOOL more=Module32FirstW(h,&m);if(!more){CloseHandle(h);need(false,"module first");}try{unsigned count=0;while(more){need(++count<=256,"module bound");fs::path p=m.szExePath;auto size=fs::file_size(p);need(size<=512ull*1024*1024,"module size bound");std::ifstream f(p,std::ios::binary);Bytes b(static_cast<size_t>(size));f.read(reinterpret_cast<char*>(b.data()),static_cast<std::streamsize>(size));need(bool(f),"module read");s+=utf8(p.filename().wstring())+"\t"+std::to_string(size)+"\t"+hash(b)+"\n";more=Module32NextW(h,&m);}}catch(...){CloseHandle(h);throw;}CloseHandle(h);note(out/"modules.tsv",s);
}
bool debugMessages(ID3D12InfoQueue* info,const fs::path& out){if(!info)return true;auto n=info->GetNumStoredMessages();need(n<=4096&&info->GetNumMessagesDiscardedByMessageCountLimit()==0,"debug capture overflow");std::string text;bool clean=true;for(UINT64 i=0;i<n;++i){SIZE_T size=0;hr(info->GetMessage(i,nullptr,&size),"debug size");need(size<=65536,"debug message bound");Bytes b(size);auto m=reinterpret_cast<D3D12_MESSAGE*>(b.data());hr(info->GetMessage(i,m,&size),"debug message");text+=std::to_string(m->Severity)+"\t"+std::to_string(m->ID)+"\t"+std::string(m->pDescription,m->DescriptionByteLength)+"\n";if(m->Severity==D3D12_MESSAGE_SEVERITY_CORRUPTION||m->Severity==D3D12_MESSAGE_SEVERITY_ERROR)clean=false;}note(out/"debug-messages.txt",text);return clean;}
struct Observation {std::string status="INCOMPLETE/ERROR",reason="unfinished",debug="unavailable";bool numeric=false;size_t wrong=0;};
Observation graphics(const Options& o,const fs::path& out,const std::map<std::string,Bytes>& files){
 Observation obs;ComPtr<ID3D12Debug> debug;HRESULT dh=D3D12GetDebugInterface(IID_PPV_ARGS(&debug));if(SUCCEEDED(dh)){debug->EnableDebugLayer();obs.debug="enabled";}note(out/"debug-layer.txt","status="+obs.debug+"\nHRESULT="+std::to_string(static_cast<unsigned long>(dh))+"\n");
 Context c;ComPtr<ID3D12InfoQueue> info;c.evidence=out;try{hr(CreateDXGIFactory2(0,IID_PPV_ARGS(&c.factory)),"DXGI factory");c.adapter=choose(c.factory.Get(),o);DXGI_ADAPTER_DESC1 ad={};hr(c.adapter->GetDesc1(&ad),"selected adapter description");LARGE_INTEGER driver={};auto drv=c.adapter->CheckInterfaceSupport(__uuidof(IDXGIDevice),&driver);note(out/"adapter.txt",adapterText(ad)+"driver_query_hresult="+std::to_string(static_cast<unsigned long>(drv))+"\ndriver_version_raw="+std::to_string(driver.QuadPart)+"\n");
 auto deviceHr=D3D12CreateDevice(c.adapter.Get(),D3D_FEATURE_LEVEL_12_0,IID_PPV_ARGS(&c.device));note(out/"device.txt","HRESULT="+std::to_string(static_cast<unsigned long>(deviceHr))+"\n");if(deviceHr==DXGI_ERROR_UNSUPPORTED){obs.status="UNSUPPORTED";obs.reason="feature level 12.0 unavailable";return obs;}hr(deviceHr,"D3D12 device");
 if(debug){hr(c.device.As(&info),"enabled debug queue");hr(info->SetMessageCountLimit(4096),"debug capture bound");}
 D3D12_FEATURE_DATA_SHADER_MODEL sm={D3D_SHADER_MODEL_6_8};auto smhr=c.device->CheckFeatureSupport(D3D12_FEATURE_SHADER_MODEL,&sm,sizeof(sm));note(out/"shader-model.txt","requested=6.8\nHRESULT="+std::to_string(static_cast<unsigned long>(smhr))+"\nreported="+std::to_string(sm.HighestShaderModel)+"\n");
 if(smhr==E_INVALIDARG||smhr==DXGI_ERROR_UNSUPPORTED||(SUCCEEDED(smhr)&&sm.HighestShaderModel<D3D_SHADER_MODEL_6_8)){obs.status="UNSUPPORTED";obs.reason="shader model 6.8 unavailable; shader unchanged";if(!debugMessages(info.Get(),out)){obs.status="INCOMPLETE/ERROR";obs.reason="severe debug messages";}modules(out);return obs;}hr(smhr,"shader model query");
 D3D12_COMMAND_QUEUE_DESC q={};q.Type=D3D12_COMMAND_LIST_TYPE_DIRECT;hr(c.device->CreateCommandQueue(&q,IID_PPV_ARGS(&c.queue)),"queue");hr(c.device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&c.allocator)),"allocator");hr(c.device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,c.allocator.Get(),nullptr,IID_PPV_ARGS(&c.list)),"list");hr(c.device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&c.fence)),"fence");D3D12_QUERY_HEAP_DESC qh={D3D12_QUERY_HEAP_TYPE_SO_STATISTICS,1,0};hr(c.device->CreateQueryHeap(&qh,IID_PPV_ARGS(&c.queries)),"query heap");
 Bytes payload;bool raw=false;
 {
 std::vector<ComPtr<ID3D12Resource>> cu,ci,cr;const char* cn[]={"synthetic-VB.bin","synthetic-CB.bin"};
 for(auto name:cn){const auto& b=files.at(name);auto u=c.buffer(b.size(),D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ,name);upload(u.Get(),b);auto d=c.buffer(b.size(),D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_COPY_DEST,name);auto r=c.buffer(b.size(),D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST,name);c.list->CopyBufferRegion(d.Get(),0,u.Get(),0,b.size());c.transition(d.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_COPY_SOURCE);c.list->CopyBufferRegion(r.Get(),0,d.Get(),0,b.size());c.transition(d.Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER);cu.push_back(u);ci.push_back(d);cr.push_back(r);}
 c.submit();bool exact=true;for(size_t i=0;i<2;++i){auto b=download(cr[i].Get(),files.at(cn[i]).size());put(out/(std::string(cn[i])+".readback.bin"),b);exact=exact&&(b==files.at(cn[i]));}note(out/"input-gate.txt",exact?"exact=true\n":"exact=false\n");need(exact,"synthetic input readback mismatch");c.reset();
 Bytes seed(candidateLayout.total,0xa5);std::fill(seed.begin()+candidateLayout.counter,seed.end(),static_cast<unsigned char>(0));auto seedBuffer=c.buffer(candidateLayout.total,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ,"SO seed");upload(seedBuffer.Get(),seed);
 auto current=stage(c,files.at("baseline.dxil"),"BASELINE",out);note(out/"allocations.tsv",c.allocations);draw(c,current,seedBuffer.Get(),ci,0);c.submit();auto result=capture(current,out);payload=result.payload;words(out,payload,files.at("oracle.bin"));raw=result.accounting&&finite(payload)&&c.allocationRequests==9&&c.allocated<=128ull*1024*1024;note(out/"raw-gates.txt",std::string("valid=")+(raw?"true\n":"false\n")+"submissions_fenced=2\ndraws=1\nexplicit_buffer_bytes="+std::to_string(c.allocated)+"\n");
 }
 c.list.Reset();c.allocator.Reset();c.queries.Reset();c.fence.Reset();c.queue.Reset();hr(c.device->GetDeviceRemovedReason(),"final device removed reason");bool clean=debugMessages(info.Get(),out);modules(out);
 obs.status=classify(payload,files.at("oracle.bin"),files.at("known-bad.bin"),raw&&clean);obs.numeric=raw&&clean;obs.reason=obs.numeric?"clean execution and complete raw gates; exact integer comparison":"invalid raw or debug gates";for(size_t i=0;i<448;i+=4)obs.wrong+=word(payload,i)!=word(files.at("oracle.bin"),i);return obs;
 }catch(const std::exception& e){obs.status="INCOMPLETE/ERROR";obs.reason=e.what();obs.numeric=false;try{if(!fs::exists(out/"debug-messages.txt"))debugMessages(info.Get(),out);}catch(...){}return obs;}
}
int wmain(int argc,wchar_t** argv){
 // Hard watchdog avoids stdio/COM/flush locks. Absence of result.json means INCOMPLETE.
 HANDLE watchdog=CreateThread(nullptr,0,[](LPVOID)->DWORD{Sleep(55000);TerminateProcess(GetCurrentProcess(),124);return 124;},nullptr,0,nullptr);if(!watchdog)return 125;CloseHandle(watchdog);
 fs::path out;bool owned=false;Observation obs;
 try{std::vector<std::wstring> args;for(int i=1;i<argc;++i)args.emplace_back(argv[i]);auto o=parse(args);if(o.mode==Mode::List){ComPtr<IDXGIFactory4> f;hr(CreateDXGIFactory2(0,IID_PPV_ARGS(&f)),"metadata-only DXGI factory");choose(f.Get(),o);return 0;}
  out=fs::absolute(o.output);need(fs::create_directory(out),"output must be a fresh directory with existing parent");owned=true;note(out/"STARTED.txt","INCOMPLETE until result.json and process exit are both checked.\n");
  auto dir=executableDir();std::map<std::string,Bytes> files;std::string identities;
  for(auto p:pins){auto b=read(dir/"data"/p.name);need(b.size()==p.bytes&&hash(b)==p.hash,std::string("input identity: ")+p.name);identities+=std::string(p.hash)+"  "+p.name+"\n";put(out/p.name,b);files.emplace(p.name,std::move(b));}
  auto hlsl=read(dir/"source/baseline.hlsl");need(hash(hlsl)=="0f1a6f974cf765f9bc54553808d693437e5a3825232e49633d954585c8563bcb","source HLSL identity");need(oracle(files.at("synthetic-VB.bin"),files.at("synthetic-CB.bin"))==files.at("oracle.bin"),"independent integer oracle");note(out/"input-identities.sha256",identities);note(out/"CPU_VERIFIED.txt","DXIL, all fixtures, source, independent integer oracle exact; maximum=5350\n");obs=graphics(o,out,files);
 }catch(const std::exception& e){obs.status="INCOMPLETE/ERROR";obs.reason=e.what();obs.numeric=false;obs.debug="see debug-layer.txt if created";}
 if(owned){try{note(out/"result.json","{\n\"classification\":"+jsonQuote(obs.status)+",\n\"reason\":"+jsonQuote(obs.reason)+",\n\"numeric_interpretation\":"+(obs.numeric?"true":"false")+",\n\"wrong_words\":"+(obs.numeric?std::to_string(obs.wrong):"null")+",\n\"total_words\":112,\n\"debug_layer\":"+jsonQuote(obs.debug)+",\n\"requires_exit_zero_for_numeric_interpretation\":true\n}\n");}catch(...){return 1;}}
 std::cout<<obs.status<<": "<<obs.reason<<std::endl;return obs.numeric?0:obs.status=="UNSUPPORTED"?2:1;
}
