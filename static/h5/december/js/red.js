$(document).ready(function() {
    var d = {'1':'6.66xianjinhongbao@2x.png','2':'8licaihongbao@2x.png','3':'25licaihongbao@2x.png','4':'30licaihongbao@2x.png','5':'55licaihongbao@2x.png','6':'66.6xianjinhongbao@2x.png','7':'100licaihongbao@2x.png','8':'230licaihongbao@2x.png','9':'275licaihongbao@2x.png','10':'588licaihongbao@2x.png','11':'666xianjinhongbao@2x.png','12':'1212licaihongbao@2x.png'};
    var i = '3';
    console.log(d[i]);

    // 点击redbutton按钮时执行以下全部
    $('.redbutton').click(function(){
        // 在带有red样式的div中添加shake-chunk样式
        $('.red').addClass('shake-chunk');
        // 点击按钮2000毫秒后执行以下操作
        setTimeout(function(){
            // 在带有red样式的div中删除shake-chunk样式
            $('.red').removeClass('shake-chunk');
            // 将redbutton按钮隐藏
            $('.redbutton').css("display" , "none");
            // 修改red 下 span   背景图
            $('.red-jg > img').attr("src" , "images/"+d[i]);
            // 修改red-jg的css显示方式为块
            $('.red-jg').css("display" , "block");
        },2000);
    });
    $(".smtc").click(function(){
        $(".guize").css("display","block");
        $(".guanbi").click(function(){
            $(".guize").hide();
        });
    });
    var doscroll = function(){
        var $parent = $('.huoj');
        var $first = $parent.find('li:first');
        var height = $first.height();
        $first.animate({
            marginTop: -height + 'px'
        }, 500, function() {
            $first.css('marginTop', 0).appendTo($parent);
        });
    };
    setInterval(function(){doscroll()}, 1000);

    /*$("#chai").click(function () {
        $(this).hide();
        $(".hongbao img").eq(6).css("display","block");
    })*/
});








