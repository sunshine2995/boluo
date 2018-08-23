$(function(){
    $(window).on('scroll',function(){
        var $scroll=$(this).scrollTop();
        if($scroll>=1){
            $('#loutinav').show();
        }else{
            $('#loutinav').hide();
        }

        $('.louti').each(function(){
            var $loutitop=$('.louti').eq($(this).index()).offset().top+400;
            if($loutitop>$scroll){
                $('#loutinav li').removeClass('active');
                $('#loutinav li').eq($(this).index()).addClass('active');
                return false;
            }
        });
    });
    
    var $loutili=$('#loutinav li').not('.last');
    $loutili.on('click',function(){
        $(this).addClass('active').siblings('li').removeClass('active');
        var $loutitop=$('.louti').eq($(this).index()).offset().top;
        $('html,body').animate({
            scrollTop:$loutitop
        })
    });
    $('.last').on('click',function(){
        $('html,body').animate({
            scrollTop:0
        })
    });
    //公司荣誉
    var $panels= $('#slider .scrollContainer > li');
	var $parent=$panels.parent();
	var $length=$panels.length;
	var $first=$panels.eq(0).clone().addClass("panel cloned").attr("id",'panel_'+($length+1));
	var $last=$panels.eq($length-1).clone().addClass("cloned").attr("id",'panel_0');;
	$parent.append($first);
	$parent.prepend($last);
	var totalPanels= $(".scrollContainer").children().size();
	var regWidth= $(".panel").css("width");
	var regImgWidth= $(".panel img").css("width");
	var movingDistance= 195;
	var curWidth= 230;
	var curHeight=260;
	var curImgWidth =230;
	var curImgHeight=180;
	var othersW=170;
	var othersH=235;
	var othersImgW =170;
	var othersImgH=130;
	var $panels= $('#slider .scrollContainer > li');
	var $container= $('#slider .scrollContainer');
	$panels.css({'float' : 'left','position' : 'relative'});
	$("#slider").data("currentlyMoving", false);
	$container.css('width', (($panels[0].offsetWidth+25) * $panels.length) + 60 ).css('left','0');
	var scroll = $('#slider .scroll').css('overflow', 'hidden');
	function returnToNormal(element) {
		$(element).animate({ width: othersW,height: othersH}).find("img").animate({width:othersImgW,height:othersImgH});
	};
	function growBigger(element) {
		$(element).addClass("current").animate({ width: curWidth,height:curHeight}).siblings().removeClass("current")
		.end().find("img").animate({width:curImgWidth,height:curImgHeight})
	}
	function change(direction) {
		if((direction && !(curPanel < totalPanels-2)) || (!direction && (curPanel <= 1))) {
			return false;
		}
		if (($("#slider").data("currentlyMoving") == false)) {
			$("#slider").data("currentlyMoving", true);
			var next         = direction ? curPanel + 1 : curPanel - 1;
			var leftValue    = $(".scrollContainer").css("left");
			var movement	 = direction ? parseFloat(leftValue, 10) - movingDistance : parseFloat(leftValue, 10) + movingDistance;
			$(".scrollContainer").stop().animate({"left": movement}, function() {
				$("#slider").data("currentlyMoving", false);
			});
			returnToNormal("#panel_"+curPanel);
			growBigger("#panel_"+next);
			curPanel = next;
			$("#panel_"+(curPanel+1)).unbind();
			$("#panel_"+(curPanel+1)).click(function(){ change(true); });														
			$("#panel_"+(curPanel-1)).unbind();
			$("#panel_"+(curPanel-1)).click(function(){ change(false); });
			$("#panel_"+curPanel).unbind();
		}
	}
	growBigger("#panel_1");	
	var curPanel = 1;
	$("#panel_"+(curPanel+1)).click(function(){ change(true);return false;});
	$("#panel_"+(curPanel-1)).click(function(){ change(false);return false;});
	$("#slider .next").click(function(){ change(true);});	
	$("#slider .prev").click(function(){ change(false);});
	$(window).keydown(function(event){
		switch (event.keyCode) {
			case 13:
				$(".next").click();
			break;
			case 37:
				$(".prev").click();
			break;
			case 39:
				$(".next").click();
			break;
		}
	});	
})