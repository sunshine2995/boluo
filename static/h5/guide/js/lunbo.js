$(document).ready(function(){
    var k=[$("#a"),$("#b"),$("#c"),$("#d")];
    for (var i=0;i<k.length;i++){
        k[i].touchSlider({
            flexible : true,
            speed : 300,
            btn_prev : k[i].children(".btn_prev"),
            btn_next : k[i].children(".btn_next"),
            /*paging : k[i].children(".point a"),
            counter : function (e){
                $(".point a").removeClass("on").eq(e.current-1).addClass("on");//图片顺序点切换
            }*/
        });

        k[i].children("a").click(function(){
            if($dragBln) {
                return false;
            }
        });
    }

});

/*
$(document).ready(function(){
    $(".main_img").touchSlider({
        flexible : true,
        speed : 300,
        btn_prev : $("#btn_prev"),
        btn_next : $("#btn_next"),
        paging : $(".point a"),
        counter : function (e){
            $(".point a").removeClass("on").eq(e.current-1).addClass("on");//图片顺序点切换
        }
    });

    $(".main_img a").click(function(){
        if($dragBln) {
            return false;
        }
    });

    $(".main_imga").touchSlider({
        flexible : true,
        speed : 300,
        btn_prev : $("#btn_preva"),
        btn_next : $("#btn_nexta"),
        paging : $(".pointa a"),
        counter : function (e){
            $(".pointa a").removeClass("on").eq(e.current-1).addClass("on");//图片顺序点切换
        }
    });

    $(".main_imga a").click(function(){
        if($dragBln) {
            return false;
        }
    });

    $(".main_imgb").touchSlider({
        flexible : true,
        speed : 300,
        btn_prev : $("#btn_prevb"),
        btn_next : $("#btn_nextb"),
        paging : $(".pointb a"),
        counter : function (e){
            $(".pointb a").removeClass("on").eq(e.current-1).addClass("on");//图片顺序点切换
        }
    });

    $(".main_imgb a").click(function(){
        if($dragBln) {
            return false;
        }
    });

    $(".main_imgc").touchSlider({
        flexible : true,
        speed : 300,
        btn_prev : $("#btn_prevc"),
        btn_next : $("#btn_nextc"),
        paging : $(".pointc a"),
        counter : function (e){
            $(".pointc a").removeClass("on").eq(e.current-1).addClass("on");//图片顺序点切换
        }
    });

    $(".main_imgc a").click(function(){
        if($dragBln) {
            return false;
        }
    });

});*/
