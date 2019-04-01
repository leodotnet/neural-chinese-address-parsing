# Chinese Address Parsing Annotation Guideline
## Goal
Recognize all the chunks (e.g. city, road, etc.) in the given Chinese address. For each chunk, the boundary and the label are required to be annotated. 

####【prov】
1. Interpretation: province, autonomous region
2. Example 1: 
	1. Query: 内蒙古赤峰市锦山镇
	2. Annotation: <font color='red'><b>prov=内蒙古</b></font> city=赤峰市 district=喀喇沁旗 town=锦山镇
3. Example 2: 
	1. Query: 渭南市大荔县户家乡边章营村
	2. Annotation: <font color='red'><b>prov=陕西省</b></font> city=渭南市 district=大荔县 town=户家乡 community=边章营村

####【city】
1. Interpretation: city,municipality,autonomous District
2. Example 1: 
	1. Query: 杭州市富阳区戴家墩路91号东阳诚心木线(富阳店)
	2. Annotation: <font color='red'><b>city=杭州市</b></font> district=富阳区 road=戴家墩路 roadno=91号 poi=东阳诚心木线(富阳店)
3. Example 2: 
	1. Query: 西藏自治区日喀则地区定日县柑碑村712号
	2. Annotation: prov=西藏自治区 <font color='red'><b>city=日喀则地区</b></font> district=定日县 community=柑碑村 roadno=712号

####【district】
1. Interpretation: district
2. Example 1: 
	1. Query: 东城区福新东路245号
	2. Annotation: <font color='red'><b>district=东城区</b></font> road=福新东路 roadno=245号

####【devzone】
1. Interpretation: economical development zone
2. Example 1: 
	1. Query: 内蒙古自治区呼和浩特市土默特左旗金川开发区公元仰山9号楼2单元202
	2. Annotation: prov=内蒙古自治区 city=呼和浩特市 district=土默特左旗 town=察素齐镇 <font color='red'><b>devzone=金川开发区</b></font> poi=公元仰山 houseno=9号楼 cellno=2单元 roomno=202室
3. Example 2: 
	1. Query: 南宁市青秀区仙葫经济开发区开泰路148号广西警察学院仙葫校区
	2. Annotation: city=南宁市 district=青秀区 <font color='red'><b>devzone=仙葫经济开发区</b></font> road=开泰路 roadno=148号 poi=广西警察学院仙葫校区

####【town】
1. Interpretation: town, administrative street;
2. Example 1: 
	1. Query: 上海市 静安区 共和新路街道 柳营路669弄14号1102
	2. Annotation: city=上海市 district=静安区 <font color='red'><b>town=共和新路街道</b></font> road=柳营路 roadno=669弄 houseno=14号 roomno=1102室
3. Example 2: 
	1. Query: 五常街道顾家桥社区河西北9号衣服鞋子店
	2. Annotation: <font color='red'><b>town=五常街道</b></font> community=顾家桥社区 road=河西北 roadno=9号 poi=衣服鞋子店

####【community】
1. Interpretation: community
2. Example 1: 
	1. Query: 张庆乡北胡乔村
	2. Annotation: town=张庆乡 <font color='red'><b>community=北胡乔村</b></font>
3. Example 2: 
	1. Query: 五常街道顾家桥社区河西北9号衣服鞋子店
	2. Annotation: town=五常街道 <font color='red'><b>community=顾家桥社区</b></font> road=河西北 roadno=9号 poi=衣服鞋子店

####【road】
1. Interpretation: road
2. Example 1: 
	1. Query: 静安区江场三路238号1613室
	2. Annotation: district=静安区 <font color='red'><b>road=江场三路</b></font> roadno=238号 roomno=1613室
3. Example 2: 
	1. Query: 沿山村5组
	2. Annotation: community=沿山村 <font color='red'><b>road=5组</b></font>
4. Example 2: 
	1. Query: 江宁区江宁滨江开发区中环大道10号环宇人力行政部
	2. Annotation: district=江宁区 town=江宁街道 devzone=江宁滨江开发区 <font color='red'><b>road=中环大道</b></font> roadno=10号 poi=环宇人力行政部
	
####【roadno】
1. Interpretation: road number
2. Example 1: 
	1. Query: 江宁区江宁滨江开发区中环大道10号环宇人力行政部
	2. Annotation: district=江宁区 town=江宁街道 devzone=江宁滨江开发区 road=中环大道 <font color='red'><b>roadno=10号</b></font> poi=环宇人力行政部
3. Example 2: 
	1. Query: 沿山村5组6号
	2. Annotation: community=沿山村 <font color='red'><b>roadno=5组6号</b></font>

####【subroad】
1. Interpretation: subroad
2. Example 1: 
	1. Query: 浙江省台州市临海市江南大道创业大道288号
	2. Annotation: prov=浙江省 city=台州市 district=临海市 town=江南街道 road=江南大道 <font color='red'><b>subroad=创业大道</b></font> subroadno=288号


####【subroadno】
1. Interpretation: subroad number
2. Example 1: See the last example。

####【poi】
1. Interpretation: point of interest；
2. Example 1: 
	1. Query: 浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区
	2. Annotation: prov=浙江省 city=杭州市 district=余杭区 town=五常街道 road=文一西路 roadno=969号 <font color='red'><b>poi=阿里巴巴西溪园区</b></font>

####【subpoi】
1. Interpretation: sub-poi；
2. Example 1: 
	1. Query: 新疆维吾尔自治区 昌吉回族自治州 昌吉市 延安北路街道 延安南路石油小区东门
	2. Annotation: prov=新疆维吾尔自治区 city=昌吉回族自治州 district=昌吉市 town=延安北路街道 road=延安南路 poi=石油小区 <font color='red'><b>subpoi=东门</b></font>
3. Example 2: 
	1. Query: 西湖区新金都城市花园西雅园10幢3底层
	2. Annotation: district=西湖区 town=文新街道 road=古墩路 roadno=415号 poi=新金都城市花园 <font color='red'><b>subpoi=西雅园</b></font> houseno=10幢 floorno=3底层
4. Example 3: 
	1. Query: 广宁伯街2号金泽大厦东区15层
	2. Annotation: road=广宁伯街 roadno=2号 poi=金泽大厦 <font color='red'><b>subpoi=东区</b></font> floorno=15层
5. Comment: We regard the second poi appearing after the first poi as subpoi if they are located in the same region.

####【houseno】
1. Interpretation: house number；
2. Example 1: 
	1. Query: 阿里巴巴西溪园区6号楼小邮局
	2. Annotation: poi=阿里巴巴西溪园区 <font color='red'><b>houseno=6号楼</b></font> person=小邮局
3. Example 2: 
	1. Query: 四川省 成都市 金牛区 沙河源街道 金牛区九里堤街道 金府机电城A区3栋16号
	2. Annotation: prov=四川省 city=成都市 district=金牛区 town=沙河源街道 road=金府路 poi=金府机电城 subpo=A区 <font color='red'><b>houseno=3栋</b></font> cellno=16号
4. Example 3: 
	1. Query: 竹海水韵春风里12-3-1001
	2. Annotation: poi=竹海水韵 subpoi=春风里 <font color='red'><b>houseno=12幢</b></font> cellno=3单元 roomno= 1001室
5. Comment: It usually appears after poi.

####【cellno】
1. Interpretation: cell number；
2. Example 1: 
	1. Query: 竹海水韵春风里12-3-1001
	2. Annotation: poi=竹海水韵 subpoi=春风里 houseno=12幢 <font color='red'><b>cellno=3单元</b></font> roomno= 1001室
3. Example 2: 
	1. Query: 蒋村花园新达苑18幢二单元101
	2. Annotation: town=蒋村街道 community=蒋村花园社区 road=晴川街 poi=蒋村花园 subpoi=新达苑 houseno=18幢 <font color='red'><b>cellno=二单元</b></font> roomno=101室

####【floorno】
1. Interpretation: floor number；
2. Example 1: 
	1. Query: 北京市东城区东中街29号东环广场B座5层信达资本
	2. Annotation: city=北京市 district=东城区 town=东直门街道 road=东中街 roadno=29号 poi=东环广场 houseno=B座 <font color='red'><b>floorno=5层</b></font> person=信达资本

####【roomno】
1. Interpretation: room number；
2. Example 1: See the example in cell number 

####【person】
1. Interpretation: name of a company or company representative
2. Example 1: 
	1. Query: 北京 北京市 西城区 广安门外街道 马连道马正和大厦3层我的未来网总部
	2. Annotation: city=北京市 district=西城区 town=广安门外街道 road=马连道 poi=马正和大厦 floorno=3层 <font color='red'><b>person=我的未来网总部</b></font>
3. Example 2: 
	1. Query: 浙江省 杭州市 余杭区 良渚街道沈港路11号2楼 常春藤公司
	2. Annotation: prov=浙江省 city=杭州市 district=余杭区 town=良渚街道 road=沈港路 roadno=11号 floorno=2楼 <font color='red'><b>person=常春藤公司</b></font>

####【assist】
1. Interpretation: assistant words for better location. For example, 旁边(beside), 对面(opposite)
2. Example 1: 
	1. Query: 广西柳州市城中区潭中东路勿忘我网吧门口
	2. Annotation: prov=广西壮族自治区 city=柳州市 district=城中区 town=潭中街道 road=潭中东路 poi=勿忘我网吧 <font color='red'><b>assist=门口</b></font>

####【redundant】
1. Interpretation: useless and redundant words
2. Example 1: 
	1. Query: 浙江省 杭州市 滨江区 浙江省 杭州市 滨江区 六和路东信大道自行车租赁点
	2. Annotation: prov=浙江省 city=杭州市 district=滨江区 redundant=<font color='red'><b>浙江省杭州市滨江区</b></font> road=六和路 subroad=东信大道 poi=自行车租赁点

3. Example 2: 
	1. Query: 浙江省 杭州市 滨江区 六和路 ---- 东信大道自行车租赁点
	2. Annotation: prov=浙江省 city=杭州市 district=滨江区 road=六和路 redundant=<font color='red'><b>----</b></font> subroad=东信大道 poi=自行车租赁点

####【otherinfo】
1. Interpretation: other information which cannot be classified

## Partial Order
There exists partial orders among labels. For example, city appears after province in the address. We summarize the following partial orders.

#### 1. prov > city > district > town > comm > road > roadno > poi > houseno > cellno > floorno > roomno
#### 2. district  > devzone
#### 3. devzone > comm
#### 4. road > subroad
#### 5. poi > subpoi

