///-------------------------------///
$(function () {
    $('.cj').luckDraw({
        width: 160, //宽
        height: 160, //高
        line: 2, //几行
        list: 3, //几列
        click: ".btttt" //点击对象
    });
});

$.fn.extend({
    luckDraw: function (data) {
        var anc = $(this); //祖父元素
        var list = anc.children("li");
        var click; //点击对象
        var lineNumber; //几行 3
        var listNumber; //几列 4
        var thisWidth;
        var thisHeight;
        if (data.line == null) {
            return;
        } else {
            lineNumber = data.line;
        }
        if (data.list == null) {
            return;
        } else {
            listNumber = data.list;
        }
        if (data.width == null) {
            return;
        } else {
            thisWidth = data.width;
        }
        if (data.height == null) {
            return;
        } else {
            thisHeight = data.height;
        }
        if (data.click == null) {
            return;
        } else {
            click = data.click;
        }

        ///---初始化
        anc.css({
            width: thisWidth * listNumber,
            height: thisHeight * lineNumber,
            position: "relative"
        });
        list.css({
            width: thisWidth,
            height: thisHeight,
            position: "absolute"
        });

        var all = listNumber * lineNumber - (lineNumber - 2) * (listNumber - 2)  //应该有的总数
        if (all > list.length) { //如果实际方块小于应该有的总数
            for (var i = 0; i < (all - list.length); i++) {
                anc.append("<li>" + all + "</li>");
            }
        }

        list = anc.children("li");
        list.css({
            width: thisWidth,
            height: thisHeight,
            position: "absolute"
        });

        list.each(function (index) {
            if (index < listNumber) {  //---小于listNumber列
                $(this).css({
                    left: index % listNumber * thisWidth
                });
            }
            else if (index >= listNumber && index < listNumber + lineNumber - 2) {
                $(this).css({
                    top: (index + 1) % listNumber * thisHeight,
                    right: 0
                });
            }
            else if (index >= listNumber + lineNumber - 2 && index < all - lineNumber + 2) {
                $(this).css({
                    bottom: 0,
                    right: (index + 2) % listNumber * thisWidth
                });
            } else {
                /*
                */
                $(this).css({
                    bottom: (index - 2) % listNumber * thisHeight,
                    left: 0
                });
            }
            if (index + 1 > all) {
                $(this).remove();
            }
        });
        var ix = 0;
        var speed = 300;
        var Countdown = 300; //倒计时
        var isRun = false;
        var dgTime = 200;

        $(document).ready(function() {
            if(enabled == 'True'){
            }else {

                //按钮置灰
                $(".btttt").addClass("zhihui").attr({"disabled":"disabled"});
            }
        });
        if (isRun) {
            return;
        } else {
            // stime = ixx;
        }
        $(".btttt").click(function () {
            $(".btttt").attr({"disabled":"disabled"});
            $.ajax({
                url: '/v1/activity/nationalday/ajax/' + phone + '/' + token,
                type: 'GET',
                async: true,
                cache: false,
                success: function (data) {
                    //  返回： {'result'：'1'}
                    //
                    ixx = data['result'];
                    var dd = { "1": '6', "2": '1' , "3": '5', "4": '4', "5": '3', "6": '2'}; // 字典
                    stime = dd[ixx];
                    $('.cj>li').css("opacity", "0.6");
                    dgTime += stime * 10 + 80;

                    uniform();
                }
            });


        });
        $(".gbjp").click(function () {
            $(".jiangp").css("display", "none");
            window.location.reload();
        });

        //$('.zt').html('已点击，结果是数字<span> '+stime+' </span>号中奖');
        //$('.cj>li').css("opacity","0.6");
        //dgTime += stime*10 + 80;

        //uniform();


        function uniform() { //匀速
            list.removeClass("adcls");
            list.eq(ix).addClass("adcls");
            ix++;
            init(ix);
            Countdown -= 50;
            if (Countdown == 0) {
                clearTimeout(stop);
                speedDown();
            } else {
                var stop = setTimeout(uniform, speed);
            }
        }

        function speedDown() { //减速
            list.removeClass("adcls");
            list.eq(ix).addClass("adcls");
            ix++;
            init(ix);
            speed += 10;
            if (speed == dgTime + 20) {
                clearTimeout(stop);
                end();
            } else {
                var stop = setTimeout(speedDown, speed);
            }
        }

        function end() {
            // if(ix == 0){
            // 	ix = 6;
            // }
            setTimeout(function () {
                $(".jiangp").css("display", "block");
                //$('.jieguo>li').html('恭喜 <span> '+ix+' </span> 号中奖');
                $(".jieguo>li:nth-child(" + ixx + ")").css("display", "block");
            }, 600);
            $(".btttt").removeAttr("disabled");

            // initB();
        }

        ///--归0
        function init(o) {
            if (o == all) {
                ix = 0;
            }
        }
    }

});   
