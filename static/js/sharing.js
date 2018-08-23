window.onload = function (){
    var windowWidth = document.body.clientWidth; //window 宽度;
	var wrap = document.getElementById('wrap');
    var tabClick = wrap.querySelectorAll('.tabClick')[0];
    var tabLi = tabClick.getElementsByTagName('li');
    
    var tabBox =  wrap.querySelectorAll('.tabBox')[0];
    var tabList = tabBox.querySelectorAll('.tabList');
    
    var lineBorder = wrap.querySelectorAll('.lineBorder')[0];
    var lineDiv = lineBorder.querySelectorAll('.lineDiv')[0];
    
    var tar = 0;
    var endX = 0;
    var dist = 0;
    
    tabBox.style.overflow='hidden';
    tabBox.style.position='relative';
    tabBox.style.width=windowWidth*tabList.length+"px";
    
    for(var i = 0 ;i<tabLi.length; i++ ){
          tabList[i].style.width=windowWidth+"px";
          tabList[i].style.verticalAlign='top';
          tabList[i].style.display='table-cell';
    }
    
    for(var i = 0 ;i<tabLi.length; i++ ){
        tabLi[i].start = i;
        tabLi[i].onclick = function(){
            var star = this.start;
            for(var i = 0 ;i<tabLi.length; i++ ){
                tabLi[i].className='';
            };
            tabLi[star].className='active';
            init.lineAnme(lineDiv,windowWidth/tabLi.length*star)
            init.translate(tabBox,windowWidth,star);
            endX= -star*windowWidth;
        }
    }
    
    function OnTab(star){
        if(star<0){
            star=0;
        }else if(star>=tabLi.length){
            star=tabLi.length-1
        }
        for(var i = 0 ;i<tabLi.length; i++ ){
            tabLi[i].className='';
        };
        
         tabLi[star].className='active';
        init.translate(tabBox,windowWidth,star);
        endX= -star*windowWidth;
    };
    
    tabBox.addEventListener('touchstart',chstart,false);
    tabBox.addEventListener('touchmove',chmove,false);
    tabBox.addEventListener('touchend',chend,false);
};
//柱状图
var chart;

var chartData = [{
    "country": "11月",
        "visits": 10
}, {
    "country": "12月",
        "visits": 11
}, {
    "country": "1月",
        "visits": 13
}, {
    "country": "2月",
        "visits": 16
}, {
    "country": "3月",
        "visits": 18
}, {
    "country": "4月",
        "visits": 20
}];


var chart = AmCharts.makeChart("chartdiv", {
    type: "serial",
    dataProvider: chartData,
    categoryField: "country",

    graphs: [{
        valueField: "visits",
        colorField: "color",
        type: "column",
        lineAlpha: 0,
        fillAlphas: 1
    }],

    chartCursor: {
        cursorAlpha: 0,
        zoomable: false,
        categoryBalloonEnabled: false
    },
});